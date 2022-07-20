#!/usr/bin/python
# coding=utf-8
import json
import re
from re import findall


def generated_code(case_id, req_method, url, body, delay_time=None,
                   pre_sql=None, end_sql=None, use_job=None,
                   assert_res=None, extract_param=None):
    param_format = 'json' if req_method.upper() in ('POST', 'PUT') else 'params'
    if url and not url.startswith('/'):
        url = '/' + url
    query_sql = ', query_sql' if pre_sql or end_sql else ''  # 是否需要数据库查询fixture
    run_job_fixture = ', run_job' if use_job else ''  # 是否需要run_job的fixture
    if use_job:
        if use_job[3] and isinstance(use_job[3], str):
            job_param = f", job_param='{use_job[3]}'"
        elif use_job[3] and isinstance(use_job[3], int):
            job_param = f", job_param={use_job[3]}"
        else:
            job_param = ''
        # (xxl_obj.job_id, xxl_obj.env, obj.job_podid, obj.job_param)
        # run_xxl_job(job_id, env, pop_id=None, job_param=None)
        use_job_code = f"""    run_job(job_id={use_job[0]}, env={use_job[1]}, pod_id='{use_job[2]}'{job_param}) 
"""
    else:
        use_job_code = ''
    delay_time_code = ''
    if delay_time:
        delay_time_code = f"""    time.sleep({delay_time}) 
"""
    pre_sql_code = ''  # 前置pre_sql查询： 如果存在, 生成前置sql_code代码
    pre_sql_in_param = ''
    if pre_sql and '$' not in pre_sql:
        pre_sql = json.loads(pre_sql)
        for sql_key, sql_value in pre_sql.items():
            if 'select' in sql_value.lower():
                pre_sql_code += f"""    {sql_key} = query_sql("{sql_value}")          
    env_vars.put("{sql_key}", {sql_key})
"""
            else:
                pre_sql_code += f"""    query_sql("{sql_value}") 
"""
    elif pre_sql and '$' in str(pre_sql):  # 后置sql 带参数入参
        # ------处理前置sql 的'$' 入参
        pre_param_passing_list = findall(r'\$\w+', str(pre_sql))
        for i in pre_param_passing_list:
            param = i.lstrip('$').strip()
            pre_sql_in_param = f"""    {param} = env_vars.get('{param}')
"""
        # ------处理前置sql 的'$' 入参结束
        pre_sql = json.loads(pre_sql)
        for end_key, sql_value in pre_sql.items():
            if 'select' in sql_value.lower():
                pre_sql_code += f"""    {end_key} = query_sql(f"{sql_value}")
    env_vars.put("{end_key}", {end_key})
"""
            else:
                pre_sql_code += f"""    query_sql("{sql_value}") 
"""
    end_sql_code = ''  # 后置sql
    end_sql_in_param = '' # 后置sql入参获取参数
    if end_sql and '$' not in end_sql:  # 后置sql, 查询数据是否落库
        end_sql = json.loads(end_sql)
        for end_key, sql_value in end_sql.items():
            if 'select' in sql_value.lower():
                end_sql_code += f"""    {end_key} = query_sql("{sql_value}")
    env_vars.put("{end_key}", {end_key})
"""
            else:
                end_sql_code += f"""    query_sql("{sql_value}")
"""
    elif end_sql and '$' in str(end_sql):  # 后置sql 带参数入参
        # ------处理后置sql 的'$' 入参，代码复用
        end_param_passing_list = findall(r'\$\w+', str(end_sql))
        for end_ in end_param_passing_list:
            end_param = end_.lstrip('$').strip()
            end_sql_in_param = f"""    {end_param} = env_vars.get('{end_param}')
        """
        # ------处理前置sql 的'$'，代码复用 入参结束
        end_sql = json.loads(end_sql)
        for end_key, sql_value in end_sql.items():
            if 'select' in sql_value.lower():
                end_sql_code += f"""    {end_key} = query_sql(f"{sql_value}")
    env_vars.put("{end_key}", {end_key})
"""
            else:
                end_sql_code += f"""    query_sql(f"{sql_value}")
"""
    param_passing_code = ''  # 入参：判断body有$, 添加入参代码 替换body中的$符号
    if '$' in str(body):
        param_passing_list = findall(r'\$\w+', str(body))
        for i in param_passing_list:
            para = i.lstrip('$').strip()
            if para not in pre_sql_code:  # 入参时判断是否已在数据库入参，有则不提取
                param_passing_code += f"""    {para} = env_vars.get('{para}')
"""
    # 处理body 带 true, false, null
    if body and isinstance(body, str):
        try:  # 用eval转json 遇到 true false 时会报错
            body = json.loads(body)  # json 处理 null .replace('null', '""')
        except Exception as e:
            print("body参数json loads报错", e)
            body = eval(body.replace('null', 'None').replace("true", "True").replace("false", "False"))
    body_code = f"    data = {body}" if body else "    data = {}"
    extract_param_code = ''  # 提取参数：判断有extract_param，返回结果添加提取参数代码
    if extract_param:
        extract_param = json.loads(extract_param)
        for k, v in extract_param.items():
            extract_param_code += f"""    env_vars.put("{k}", res.search("{v}"))
"""

    assert_code = ''  # 断言：判断有断言语句assert_res 就添加断言代码，且格式是json
    if assert_res:
        try:
            assert_res = eval(assert_res) if isinstance(assert_res, str) else assert_res
        except:
            assert_res = json.loads(assert_res) if isinstance(assert_res, str) else assert_res
        for expression, expression_value in assert_res.items():
            assert_code += f"""    assert res.search("{expression}") == "{expression_value}"
"""

    # 最终代码用例模版
    code_template = f"""# coding=utf-8
import time
from api_case.create_project.utils import request   


def test_{case_id}(header, fake, env_vars{query_sql}{run_job_fixture}):
{use_job_code}
{delay_time_code}
{pre_sql_in_param}
{pre_sql_code}
    url = env_vars.domain + "{url}"
{param_passing_code}
{body_code}
    res = request("{req_method}", url=url, headers=header, {param_format}=data)
    assert res.status_code < 400
{extract_param_code} 
{end_sql_in_param}
{end_sql_code}
{assert_code}"""

    def param_replace1(matched):  # 去掉最终模版的 $
        obj = matched.group().strip('"\'$').strip("'")
        return obj

    def param_replace2(matched):  # 去掉最终模版的 #
        # print(matched.group())
        if 'fa.' in matched.group():
            obj2 = "fake." + matched.group().strip('"\'#').strip("'")
        else:
            obj2 = "fake." + matched.group().strip('"\'#').strip("'")
        # print(obj2)
        return obj2

    def param_replace3(matched):  # 处理前置、后置sql 里面有入参的情况
        # print(matched.group())  # ='$order_number'
        obj = matched.group().rstrip("'").replace("='$", "='{").replace("= '$", "='{") + "}'"
        # print(obj, "obj11")
        return obj
    code_template = re.sub(r'(\=\'|\=\s\')\$\S+\'', param_replace3, code_template)
    code_template = re.sub(r'\'\$\S+\'', param_replace1, code_template)
    code_template = re.sub(r'''('|")\#\#\w+((\.|)\S+'|\(\S*\s*\S*"|\(\w\)'|'|\(\)\')''',
                           param_replace2,
                           code_template)
    return code_template


def env_vars_code(definition):
    """run方法运行时，调用此方法合成环境变量代码，写入到临时项目"""
    code = f"""# coding=utf-8
\"\"\"run.py创建的项目环境文件\"\"\"
from api_case.create_project.utils import MyDB
from api_case.create_project.fixture import *


@pytest.fixture(scope="session")
def env_vars(config):
    class Clazz(CaseVars):
        env = config["env"]
        mapping = {{
            {definition}
        }}      
        domain = mapping[env]["domain"]
        # 数据库写的读取联调环境数据库。不支持其他环境
        mysql_engine = MyDB("10.0.1.31",
                            "3306",
                            "nextop",
                            "Max0gl1Daup0nUR6",
                            "nextop")

    return Clazz()
"""
    return code


def combined_case(code_list: list):
    """
    组合用例方法：把单用例的数据，拼接成组合代码，run执行组合用例时写入到test_cases_(用例id)
    :param code_list: 传参单接口用例代码的列表，列表里面是字典，key是 code
    :return:
    """
    combined_code = ''
    for code in code_list:
        if not combined_code:
            combined_code = code
        else:
            data = code.split("\n", 3)[-1]
            combined_code += data

    return combined_code


conf_yaml_content = """env: daily
cookie: SESSION=ZWVkNzI4NDItYTZjMy00Y2U4LTllMTAtMmJjYWYzY2FmMDZm; satoken=cbcf2dcb-6ca9-4fe5-812c-b08bd1b4bcba"""

conftest_content = """# coding=utf-8
import os
import time
import pytest
import datetime
from random import randint, uniform

# 项目目录路径
_project_dir = os.path.dirname(os.path.abspath(__file__))


# 设置缓存
@pytest.fixture(scope="session", autouse=True)
def _project_cache(request):
    request.config.cache.set("project_dir", _project_dir)


# 自动导入fixtures
_fixtures_dir = os.path.join(_project_dir, "fixtures")
_fixtures_paths = []
for root, _, files in os.walk(_fixtures_dir):
    for file in files:
        if file.startswith("fixture_") and file.endswith(".py"):
            full_path = os.path.join(root, file)
            import_path = full_path.replace(_fixtures_dir, "").replace("\\\\", ".").replace("/", ".").replace(".py", "")
            _fixtures_paths.append("fixtures" + import_path)
pytest_plugins = _fixtures_paths

def RandomInt(begin,end):
    return randint(int(begin),int(end))

def RandomFloat(begin,end,):
    return round(uniform(float(begin),end),2)

def ReturnNowTime(format=None):
    if format != None:
        return datetime.datetime.now().strftime(format)
    else:
        return datetime.datetime.now()

def random_str(random_length=None):
    random_length = 6 if random_length == None else random_length
    string = ''
    chars = 'AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789@$#_%?'
    length = len(chars) - 1
    for i in range(random_length):
        string += chars[randint(0, length)]
    return string

"""

pytest_ini_content = """[pytest]
addopts = -s 
markers =
    smoke: smoke test
    regress: regress test
"""

fixture_env_vars_content = """# coding=utf-8
from api_case.create_project.utils import MyDB
from api_case.create_project.fixture import *


@pytest.fixture(scope="session")
def env_vars(config):
    class Clazz(CaseVars):
        env = config["env"]
        mapping = {
            "daily": {"domain": "https://api.nextop.com"},
            "nextop-pre":  {"domain": "http://api.nextop.com"},
            "nextop-prod": {"domain": "http://api.nextop.com"},
        }
        domain = mapping[env]["domain"]
        mysql_engine = MyDB("rm-wz9w784qxb36v791h.mysql.rds.aliyuncs.com",
                            "3306",
                            "nextop",
                            "Max0gl1Daup0nUR6",
                            "nextop")

    return Clazz()
"""
