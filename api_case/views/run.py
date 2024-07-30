# encoding=utf-8
import json
import os
import time
import platform
import subprocess
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from random import randint
import requests
import yaml
from threading import Thread
from django.core.exceptions import ObjectDoesNotExist

from rest_framework.decorators import api_view
from rest_framework.response import Response

from api_case.models import Case, CaseGroup, CaseResult, CaseTestReport
from api_case.serializers import CaseResultSerializer, CaseTestReportSerializer
from api_case.create_project import cli_project
from api_case.create_project.sample_code import env_vars_code
from test_management.models import projectMent, ErpAccount
from utils.api_response import jwt_token, MyThread


def fixture_filename(fixture_id):
    return f"fixture_{str(fixture_id)}.py"


class ProjectPath:
    _views_dir = os.path.dirname(os.path.abspath(__file__))
    _root_dir = os.path.dirname(_views_dir)
    projects_root = os.path.join(_root_dir, "projects")
    init_filepath = os.path.join(projects_root, "__init__.py")
    export_dir = os.path.join(projects_root, "export")

    def __init__(self, project_id, env_name, user_id):
        # 初始化目录文件
        if not os.path.exists(self.projects_root):
            os.mkdir(self.projects_root)
        if not os.path.exists(self.init_filepath):
            with open(self.init_filepath, "w"):
                pass
        if not os.path.exists(self.export_dir):
            os.mkdir(self.export_dir)

        self.project_id = project_id
        # 项目临时目录名称
        self.project_temp_name = f"project_{str(project_id)}_{env_name}_{user_id}"

    def project_temp_dir(self):
        # 项目临时目录路径
        return os.path.join(self.projects_root, self.project_temp_name)


def startproject(project_name):
    if platform.system().lower() == 'windows':
        # print('当前是windows系统')
        subprocess.call(f"python {cli_project.__file__} startproject {project_name}", shell=True)
    elif platform.system().lower() == 'linux':
        # print('当前是linux系统')
        subprocess.call(f"python3 {cli_project.__file__} startproject {project_name}", shell=True)


def write_fixture_env_vars_file(project_id, env_var, fixtures_dir):
    # fixture_env_vars.py  写入项目host, 运行环境联调标签名
    project_host = projectMent.objects.get(id=project_id)
    definition = f'"{env_var}": {{"domain": "{project_host.host}"}},'
    filepath = os.path.join(fixtures_dir, "fixture_env_vars.py")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(env_vars_code(definition))


def write_case_file(tests_dir, case_id, code):
    # 用例代码写入文件
    case_filename = f"test_{str(case_id)}.py"
    filepath = os.path.join(tests_dir, case_filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        print("用例写入失败, 请检查case.code是否正常:", e)
    return filepath


def write_conf_yaml(project_dir, env_name, env_cookie):
    # conf.yaml
    filepath = os.path.join(project_dir, "conf.yaml")
    f = open(filepath, "r", encoding="utf-8")
    conf = yaml.load(f.read(), Loader=yaml.FullLoader)
    f.close()
    conf["env"] = env_name
    conf["cookie"] = env_cookie
    with open(filepath, "w", encoding="utf-8") as f:
        yaml.dump(conf, f)


def pull_env_files(project_id, project_dir, run_env, run_cookie):
    # 获取env, conf 代码写入文件
    fixtures_dir = os.path.join(project_dir, "fixtures")
    write_fixture_env_vars_file(project_id, run_env, fixtures_dir)
    write_conf_yaml(project_dir, run_env, run_cookie)


def pull_case_files(tests_dir, cases):
    # 从数据库拉用例 code写入文件
    for case in cases:
        filepath = write_case_file(tests_dir, case.id, case.code)
        yield case.id, filepath


def delete_case_result(case_id, case_type, run_user_nickname):
    # 删除该用户执行用例id的历史执行记录
    try:
        instance = CaseResult.objects.get(
            case_id=case_id, case_type=case_type, run_user_nickname=run_user_nickname)
        instance.delete()
    except ObjectDoesNotExist:
        pass


def pytest_subprocess(cmd, case_id, case_type, run_env, run_user_nickname):
    # 执行pytest命令
    output = subprocess.getoutput(cmd)
    return output, cmd, case_id, case_type, run_env, run_user_nickname


def run_pytest(newest_case, case_type, run_user_nickname, tests_dir, run_env):
    case_id, filepath = newest_case
    delete_case_result(case_id, case_type, run_user_nickname)  # 删除历史记录
    os.chdir(tests_dir)
    print("**********用例运行目录：", tests_dir)
    cmd = rf"pytest -q {filepath}"  # pytest命令  单用例使用
    args = (pytest_subprocess, cmd, case_id, case_type, run_env, run_user_nickname)  # 运行参数
    return args


def get_res(res_data):
    try:
        response = json.loads(res_data)  # 返回结果，是在output里面，str转dict
    except Exception as e1:
        print("结果转json异常", e1, '\n', res_data)
        response = {"结果转json异常": res_data}
    return response


def get_output(result_list, res, case_type):
    if 'error' not in res and 'failed' not in res:  # 全部pass
        if case_type in [1, 11, 3]:  # 用例类型是单用例
            get_response = get_res(result_list[0])  # res_data.split("\n")[0]
        else:  # 用例类型是组合用例
            res_list = []
            for res_line in result_list:
                if 'url' in res_line and 'response' in res_line:
                    res_list.append(get_res(res_line.strip('.')))
                # print(res_line)
            get_response = {"case_res": res_list}
    else:  # 处理有失败的结果  error  failed
        if case_type in [1, 11, 3]:  # 单用例，返回结果只有1个
            get_response = get_res(result_list[0])
            get_response.update({"error_reason": result_list[-2]})  # 加入失败原因
        else:  # 组合用例，返回结果有多个
            res_list, fail_list = [], []
            for res_line in result_list:
                if 'url' in res_line and 'response' in res_line:
                    res_list.append(get_res(res_line.strip('.F')))
                elif 'FAILED test_' in res_line:
                    fail_list.append(res_line)
                else:
                    fail_list.append(res_line)
            get_response = {"case_res": res_list, "assert_data": fail_list}
    return get_response


def save_case_result(pytest_result):  # 批量执行才用此处保存
    pass_list, failed_list = [], []
    output, cmd, case_id, case_type, run_env, run_user_nickname = pytest_result  # .result()
    result_list = output.split("\n")  # 获得输出的结果列表
    summary = result_list[-1]  # 结果的最后一行是汇总 1 passed in 0.15s
    try:
        result_, elapsed, = summary.strip("=").strip().split(" in ")  # 2 failed, 1 passed in 0.52s'
        result = result_.split(" ")
        res = result[-1] if case_type in (1, 11) else result_  # 获取pytest返回结果，类型1，11时单用例
        elapsed = elapsed.split(" ")[0]
        if 'error' not in res and 'failed' not in res:  # 只有pass时才算通过
            pass_list.append('g_' + str(case_id)) if case_type == 22 else pass_list.append(case_id)
        else:
            failed_list.append('g_' + str(case_id)) if case_type == 22 else failed_list.append(case_id)
        # 解析组合用例 返回结果带多个用例结果
        # 处理测试结果
        get_response = get_output(result_list, res, case_type)
        data = {
            "caseId": case_id,
            "case_type": case_type,
            "result": res,
            "elapsed": elapsed,
            "output": get_response,
            "runEnv": run_env,
            "runUserNickname": run_user_nickname
        }
        try:
            instance = CaseResult.objects.get(
                case_id=case_id, case_type=case_type, run_user_nickname=run_user_nickname)
            serializer = CaseResultSerializer(data=data, instance=instance)  # 更新
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except ObjectDoesNotExist:  # 新增
            serializer = CaseResultSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return pass_list, failed_list
    except Exception as e:
        print("用例结果异常： ", e)
        return pass_list, failed_list


@api_view(['POST'])
def run_case(request, **kwargs):  # 单用例、单组合用例执行接口
    request_url = request.META.get("PATH_INFO")
    # case_id = request.data.get("case_id")
    # cases_id = request.data.get("cases_id")
    run_env = request.data.get("runEnv")  # 运行环境
    run_cookie = request.data.get("runCookie")  # 运行账号
    run_user_nickname = jwt_token(request)['username']  # 运行人
    user_id = jwt_token(request)["userId"]  # 用户id
    # 获得租户id ,调接口进行切换到该租户
    if not run_env or not run_cookie:
        return Response(data={"code": 50000, "msg": "运行环境与运行账号必填！"})
    try:
        tenant = ErpAccount.objects.get(cookie=run_cookie, is_del=1).tenantId  # 获得运行租户
        get_tenant(run_env, run_cookie, tenant) if tenant else ""  # 调用接口进行切换到该租户
        print("切换到租户id:", tenant)
    except Exception as e:
        print("切租户异常", e)
    case_id = kwargs["pk"]  # 用例id
    if 'cases' in request_url:  # 从组合数据库用例取case id 给用例，不同用例存到不同文件夹
        case = CaseGroup.objects.get(id=case_id)
        case_file_name = 'test_case_group'
        case_type = 2
    else:  # 从单接口数据库取case id 给用例
        case = Case.objects.get(id=case_id)
        case_file_name = 'case'
        case_type = 1
    project_id = case.project_id  # 项目id
    p = ProjectPath(project_id, run_env, user_id)  # 项目目录文件

    if not os.path.exists(p.project_temp_dir()):
        os.chdir(p.projects_root)
        print("创建pytest项目目录…………")
        startproject(p.project_temp_name)  # 使用命令创建pytest脚手架
    pull_env_files(project_id, p.project_temp_dir(), run_env, run_cookie)  # 从数据库拉取最新代码写入文件
    print("********测试项目环境搭建完成！********")

    thread_pool = ThreadPoolExecutor()  # 多线程
    tests_dir = os.path.join(p.project_temp_dir(), case_file_name)
    for newest_case in pull_case_files(tests_dir, [case]):  # [case]单个用例
        delete_case_result(case_id, case_type, run_user_nickname)  # 删除历史的执行记录
        args = run_pytest(newest_case, case_type, run_user_nickname, tests_dir, run_env)
        pytest_result = thread_pool.submit(*args)
        # print("\n pytest返回用例结果:", pytest_result.result(), '\n')
        output, cmd, case_id, case_type, run_env, run_user_nickname = pytest_result.result()

        result_list = output.split("\n")  # 获得输出的结果列表
        summary = result_list[-1]  # 结果的最后一行是汇总 1 passed in 0.15s
        result_, elapsed, = summary.strip("=").strip().split(" in ")  # 
        result = result_.split(" ")  # 1 passed
        res = result[-1] if case_type == 1 else result_
        elapsed = elapsed.split(" ")[0]
        get_response = get_output(result_list, res, case_type)
        data_res = {
            "caseId": case_id,
            "case_type": case_type,
            "result": res,
            "elapsed": elapsed,
            "output": get_response,
            "runEnv": run_env,
            "runUserNickname": run_user_nickname
        }
        try:
            instance = CaseResult.objects.get(
                case_id=case_id, case_type=case_type, run_user_nickname=run_user_nickname)
            serializer = CaseResultSerializer(data=data_res, instance=instance)  # 更新
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except ObjectDoesNotExist:  # 新增
            serializer = CaseResultSerializer(data=data_res)
            serializer.is_valid(raise_exception=True)
            serializer.save()
    return Response(data={"code": 10000, "msg": "用例运行成功", 'data': serializer.data})


@api_view(['POST'])  # 批量运行用例
def run_batch_case(request):
    case_list = request.data.get("caseList")  # 获得选中 单用例的id列表
    case_group_list = request.data.get("caseGroupList")  # 获得选中 组合用例的id列表
    project_id = request.data.get("projectId")  # 获得选中用例的id列表
    run_env = request.data.get("runEnv")  # 运行环境
    run_cookie = request.data.get("runCookie")  # 运行账号
    run_user_nickname = jwt_token(request)['username']  # 运行人
    user_id = jwt_token(request)["userId"]  # 用户id
    now = time.strftime("%Y%m%d%H%M%S", time.localtime())
    report_name = f"【批量执行】_{now}_{run_user_nickname}"
    t = Thread(target=run_func,
               args=(
                   report_name, project_id, case_list, case_group_list, run_env, run_cookie, user_id,
                   run_user_nickname,))
    t.start()
    return Response(data={"code": 10000, "msg": "批量运行成功, 请在测试计报告页查看结果！"})


# 批量运行用例入口，返回用例执行结果
def run_func(report_name, project_id, case_list, case_group_list, run_env, run_cookie, user_id, run_user_nickname):
    try:
        tenant = ErpAccount.objects.get(cookie=run_cookie, is_del=1).tenantId  # 获得运行租户
        get_tenant(run_env, run_cookie, tenant) if tenant else ""  # 组合用例调用接口进行切换到该租户
        print("切换到租户id:", tenant)
    except Exception as e:
        print("切租户异常", e)
    case_num = len(case_list) if case_list else 0
    case_group_num = len(case_group_list) if case_group_list else 0
    result = {
        "case_id": case_list,
        "case_group_id": case_group_list,
        "report_name": report_name,
        "run_cookie": run_cookie,
        "run_env": run_env,
        "case_num": case_num + case_group_num,
        "run_user_nickname": run_user_nickname,
        "report_status": 0
    }
    # 批量执行生成一条测试报告记录, 存储到数据库，后续执行完成会更新报告名称更新执行结果
    serializer = CaseTestReportSerializer(data=result)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    p = ProjectPath(project_id, run_env, user_id)  # 项目目录文件
    if not os.path.exists(p.project_temp_name):
        os.chdir(p.projects_root)
        startproject(p.project_temp_name)  # 使用命令创建pytest脚手架
    pull_env_files(project_id, p.project_temp_dir(), run_env, run_cookie)  # 从数据库拉取最新代码写入文件
    print("********测试项目环境搭建完成！********")
    start_time = time.time()
    pass_list, failed_list, res_list, thread_list = [], [], [], []   # 结果列表
    if case_group_list:  # 从组合数据库用例取case id 给用例
        case = CaseGroup.objects.filter(id__in=case_group_list)
        case_file_name = 'test_cases_group'
        # 22标识批量执行组合用例，4表示计划执行 组合用例
        case_type = 22 if "【批量执行】_" in report_name else 4
        t = MyThread(run_batch, args=(
            pass_list, failed_list, p, case_file_name, case, case_type, run_env, run_user_nickname,))
        thread_list.append(t)
        t.start()

    if case_list:  # 从单接口数据库取case id 给用例
        case = Case.objects.filter(id__in=case_list)
        case_file_name = 'test_cases'
        # 1标识批量执行单用例，3表示计划执行 单用例
        case_type = 11 if "【批量执行】_" in report_name else 3
        t = MyThread(run_batch, args=(
            pass_list, failed_list, p, case_file_name, case, case_type, run_env, run_user_nickname,))
        thread_list.append(t)
        t.start()

    for t in thread_list:
        t.join()
        res = t.get_result()
        if res:
            res_list.append(res)
    result = "Pass" if not failed_list else "Fail"
    elapsed = time.time() - start_time  # 获取总执行时间
    data = {
        "case_id": case_list,
        "case_group_id": case_group_list,
        "report_name": report_name,
        "run_cookie": run_cookie,
        "run_env": run_env,
        "case_num": case_num + case_group_num,
        "run_user_nickname": run_user_nickname,
        "pass_num": len(pass_list),
        "lose_num": len(failed_list),
        "pass_id": pass_list,
        "lose_id": failed_list,
        "elapsed": str(round(elapsed, 2)) + 's',
        "report_status": 1,
        "result": result
    }
    instance = CaseTestReport.objects.get(id=serializer.data["id"])
    serializer = CaseTestReportSerializer(instance, data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    print("批量执行完成!")
    return data


def run_batch(pass_list, failed_list, p, case_file_name, case, case_type, run_env, run_user_nickname):
    """
    批量运行用例方法
    :param pass_list:
    :param failed_list:
    :param p:
    :param case_file_name:
    :param case:
    :param case_type:
    :param run_env:
    :param run_user_nickname:
    :return: pass_list 成功的id，failed_list 失败的id
    """
    thread_pool = ThreadPoolExecutor(max_workers=200)  # 多线程
    tests_dir = os.path.join(p.project_temp_dir(), case_file_name)
    run_result = []  # 获得返回结果列表
    # 多线程并发执行用例
    for newest_case in pull_case_files(tests_dir, case):
        case_id, filepath = newest_case
        delete_case_result(case_id, case_type, run_user_nickname)  # 删除历史记录
        os.chdir(tests_dir)
        cmd = rf"pytest -qs {filepath}"  # pytest命令 ， 批量执行用
        args = (pytest_subprocess, cmd, case_id, case_type, run_env, run_user_nickname)
        run_result.append(thread_pool.submit(*args))
    # 批量获取线程的执行结果通过列表
    for future in as_completed(run_result):
        p, f = save_case_result(future.result())
        if p:
            pass_list += p
        if f:
            failed_list += f
    return pass_list, failed_list


def get_tenant(env, cookie, tenant_id):
    r = requests.session()
    now_time = str(time.time() * 1000 + randint(0, 10000000))
    r.headers = {'content-type': 'application/json',
                 'x-ca-reqid': now_time,
                 'x-ca-reqtime': now_time.split('.')[0],
                 'cookie': cookie,
                 'canary': env
                 }
    v2 = r.post('https://api.nextop.com/user/tenant/switch/v2', json={
        'sysIdentification': 1,
        'tenantId': tenant_id
    }).json()
    if v2['code'] != '000000':
        print('切换租户失败')
        return '切换租户失败'
