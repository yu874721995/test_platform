# coding=utf-8
import json
import logging
import time

from dictdiffer import diff
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api_case.models import Case, CaseResult, MitData, SwaggerApi, CaseGroup
from api_case.serializers import CaseResultSerializer, CaseListSerializer, CaseCodeSerializer, CaseGroupListSerializer
from test_tools.models import xxjobMenu, Assembly_line
from utils.api_response import MyResponse, jwt_token

logger = logging.getLogger(__name__)


@api_view(['POST'])
def case_page(request):
    query = Q()
    project_id = request.data.get("projectId")
    if project_id:  # 如果传了用例id
        query &= Q(project_id=project_id)
    exact = request.data.get("exact")  # 传了 精确匹配用例唯一的only_api, 返回已有接口
    if exact:
        query &= Q(only_api=exact)
    case_id = request.data.get("caseId")
    if case_id:  # 如果传了用例id
        query &= Q(id=case_id)
    name = request.data.get("name")
    if name:  # 如果传了用例名称
        query &= Q(name__icontains=name)
    url = request.data.get("url")
    if url:  # 如果传了接口路径
        query &= Q(url__icontains=url)
    create_user = request.data.get("create_user")
    if create_user:  # 如果传了接口路径
        query &= Q(creator_nickname__icontains=create_user)
    tag = request.data.get('tag')
    if tag:  # 如果传了标签 "1,2"
        tag = str(tag).strip("'").strip('"').split(',')
        if len(tag) == 1:
            query &= Q(tag=tag[0])
        elif len(tag) == 2:
            query &= Q(tag=tag[0]) | Q(tag=tag[1])
        elif len(tag) == 3:
            query &= Q(tag=tag[0]) | Q(tag=tag[1]) | Q(tag=tag[2])
    modules = request.data.get("module")
    if modules:  # 如果传模块[[15, 90], [1]] <class 'list'>
        query_m = Q()
        for module in modules:
            if len(module) == 1:
                print('[' + str(module[0]) + ',')
                query_m |= Q(module__icontains='[' + str(module[0]) + ',')
            else:
                query_m |= Q(module__icontains=module)
        query &= query_m
    queryset = Case.objects.filter(query).order_by('-id')  # 按照用例id倒序
    p = Paginator(queryset, request.data['size'])
    page = request.data['page']
    size = request.data['size']
    total_page = p.num_pages
    total_num = p.count  # 总页数
    case_data = [] if page not in p.page_range else p.page(page).object_list
    serializer = CaseListSerializer(case_data, many=True)  # 单页序列化
    data = {"code": 10000, "msg": "查询成功",
            'page': page,  # 当前页数
            'size': size,  # 每页展示数据的数量
            'totalNum': total_num,  # 总页数
            'totalPage': total_page,  # 总数据数量
            'data': serializer.data}
    return Response(data)


class CaseViewSet(ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseListSerializer

    def create(self, request, *args, **kwargs):
        if request.data.get("url") and not request.data.get("url").startswith('/'):
            request.data['url'] = '/' + request.data['url']
        user_name = jwt_token(request)['username']
        request.data['creator_nickname'] = user_name
        # 从流水线id 获取xxl job执行的pod_ip
        if request.data.get("assembly_id"):
            try:
                assembly = Assembly_line.objects.get(id=request.data.get("assembly_id"))
                request.data["job_podid"] = f" http://{assembly.popId}:9999/"  # http://10.244.17.232',
                # print(request.data["job_podid"])
            except Exception as e:
                print("获取流水线失败", e)
        # 没有加断言，自动加上业务断言 000000
        assert_res = request.data.get('assert_res')
        request.data['assert_res'] = assert_res if assert_res else {"code": "000000"}
        tag_list = request.data['tag']
        for i in tag_list:
            request.data['tag'] = i
            serializer = CaseCodeSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            res = serializer.data  # 调序列化生成 用例code
        return Response(
            data={"code": 10000, "msg": "用例添加成功"},
            status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not request.data.get("url").startswith('/'):
            request.data['url'] = '/' + request.data['url']
        # 从流水线id 获取xxl job执行的pod_ip
        if request.data.get("assembly_id"):
            try:
                assembly = Assembly_line.objects.get(id=request.data.get("assembly_id"))
                request.data["job_podid"] = f" http://{assembly.popId}:9999/"  # http://10.244.17.232',
                # print(request.data["job_podid"])
            except Exception as e:
                print("获取流水线失败", e)
        else:
            Case.objects.filter(id=request.data.get("id")).update(assembly_id=None)
        tag_list = request.data['tag']
        # 没有加断言，自动加上业务断言 000000
        assert_res = request.data.get('assert_res')
        request.data['assert_res'] = assert_res if assert_res else {"code": "000000"}
        num = 0
        for i in tag_list:
            request.data['tag'] = i
            if num == 0:  # 修改成多个标签时。第一次更新原有的
                partial = kwargs.pop('partial', False)
                instance = self.get_object()
                serializer = CaseCodeSerializer(instance, data=request.data, partial=partial)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                if getattr(instance, '_prefetched_objects_cache', None):
                    instance._prefetched_objects_cache = {}
                num += 1
            else:  # 第二次走新创建用例
                serializer = CaseCodeSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
            res = serializer.data  # 调序列化生成用例code
        return Response(data={"code": 10000, "msg": "用例更新成功"})  # , 'data': serializer.data

    def perform_update(self, serializer):
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return MyResponse(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(data={"code": 10000, "msg": "删除成功"}, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        instance.delete()


@api_view(['POST'])
def convert(request):  # mitmproxy抓包数据 编辑里面转换用例接口
    req_data = request.data
    req_data['creator_nickname'] = jwt_token(request)['username']
    case_id = req_data.get('case_id')
    convert_data = dict()
    if case_id:
        # 用户选择了条用例，进行参数"覆盖"
        Case.objects.filter(id=case_id, tag=1).update(single_body=req_data['single_body'])
        convert_data["更新"] = f"MitId {str(req_data['id'])} '参数更新到用例: {case_id}"
    else:  # 没有传id用户选择新增
        req_data['source'] = "抓包"
        req_data['tag'] = 1
        # req_data['name'] = req_data['only_api'] = req_data['req_method'] + req_data['url']
        serializer = CaseCodeSerializer(data=req_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        convert_data["新增"] = f"MitId {str(req_data['id'])} '生成用例: {str(serializer.data['id'])}"

    return Response(data={"code": 10000, "msg": "操作成功", "data": convert_data})


@api_view(['POST'])
def batch_convert(request):  # mitmproxy抓包数据 批量转换用例接口
    user_name = jwt_token(request)['username']
    start_time = time.time()
    mit_id_list = request.data.get('mitIdList')
    project_id = request.data.get('project_id')
    module = request.data.get('module')
    # mit_data_list 是前端传的id ,查出来的批量数据, 即请求数据
    mit_data_list = MitData.objects.filter(id__in=mit_id_list).values(
        "id", "only_api", "module", 'tag', 'req_method', 'url', 'single_body', 'assert_res')
    add_exist_list, add_list, no_change_list = [], [], []
    convert_data = dict()
    for req_data in mit_data_list:
        req_data['creator_nickname'] = user_name
        req_data['project_id'] = project_id
        req_data['module'] = module
        add_exist, add, no_change = mit_convert(req_data)
        if add_exist:
            add_exist_list.append(add_exist)
            convert_data["已转成用例"] = add_exist_list
        if add:
            add_list.append(add)
            convert_data["已生成用例"] = add_list
        if no_change:
            no_change_list.append(no_change)
            convert_data["不转换-已有用例参数key相等"] = no_change_list

    print("总耗时", time.time() - start_time)
    return Response(data={"code": 10000, "msg": "操作成功", "data": convert_data})


def mit_convert(req_data):  # 抓包转用例逻辑的公共方法
    req_data['source'] = "抓包"
    add_exist, no_change, add_id = '', '', ''
    only_api = req_data['req_method'] + req_data['url']  # 请求参数的only_api
    req_data['name'] = req_data['only_api'] = only_api  # 给用例接口参数传name
    req_data['tag'] = 1
    if not isinstance(req_data['single_body'], dict):
        single_body = req_data['single_body'] = eval(
            req_data['single_body'].replace('null', 'None').replace('false', 'False'))
        # 从数据库获得 mit数据的请求参数
    else:
        single_body = req_data['single_body']
    if isinstance(req_data['single_body'], str):
        req_data['assert_res'] = eval(req_data['assert_res'].replace('null', 'None').replace('false', 'False'))
    # -- 代码复用上面的转用例逻辑 --
    case_only_api = Case.objects.filter(only_api=only_api, tag=1)  # 匹配查找用例的唯一接口名
    if case_only_api:  # 用例里面已有相同接口
        case_params = []  # 把获取到的用例的 参数都存到参数库
        for i in case_only_api:
            if i and i.single_body and i.single_body != '':
                logger.info('报错内容:{}，类型：{}'.format(i.single_body, type(i.single_body)))
                case_params.append(eval(
                    i.single_body.replace('null', 'None').replace('false', 'False').replace('true', 'True')))
        if single_body in case_params:  # 如果转的接口数据 与某个用例参数一样，那就不需要转
            no_change = req_data['id']  # 记录不需要转用例的 mit id
        else:  # 用例里面有该接口，但参数不一致，新增
            serializer = CaseCodeSerializer(data=req_data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            add_exist = f"MitId {str(req_data['id'])} '生成用例: {str(serializer.data['id'])}"
    else:  # 用例里面没有该接口，新增
        serializers = CaseCodeSerializer(data=req_data)
        serializers.is_valid(raise_exception=True)
        serializers.save()
        add_id = f"MitId {str(req_data['id'])} '生成用例: {serializers.data['id']}"
    return add_exist, add_id, no_change


@api_view(['POST'])
def swagger_convert(request):  # swagger 接口 单条转换用例接口
    req_data = request.data
    req_data['creator_nickname'] = jwt_token(request)['username']
    req_data['tag'] = 1
    req_data['source'] = "接口"
    only_api = req_data['only_api']  # swagger参数的only_api
    single_body = req_data.get('params')  # 获取请求的接口参数
    res_list = []
    case_only_api = Case.objects.filter(only_api=only_api, tag=1)  # 匹配查找用例的唯一接口名
    if case_only_api:  # 用例里面已有相同接口
        # print("查询到已有的用例数量：", len(case_only_api), case_only_api)
        for case in case_only_api:  # 循环相同接口的 多条用例
            exist_data = case.single_body
            # print(exist_data, type(exist_data), case.id)
            exist_data = eval(exist_data) if exist_data else {}  # 把 数据库取出来的用例参数转成 字典
            result = list(diff(exist_data, single_body))  # 原用例参数与 新参数对比，相等时取新参数
            flag = False
            if result:  # 对比后存在 差异，需要对差异进行进一步判断
                for i in result:  # 循环取对比的结果
                    # ('remove', '', [('orderCreateEndTime', 1650988799000), ('pageNo', 1)])
                    if i[0] == 'remove':  # 原有参数有被移除, 把原有用例的参数也移除
                        for remove_key in i[-1]:
                            exist_data.pop(remove_key[0], None)  # 用例的字典数据移除该key
                            # case_result[f"用例{case.id}"] = "有参数被删除，全部用例换成最新参数！"
                            res_list.append(f"用例id {case.id}  {remove_key[0]}参数被移除，已移除该参数")
                        flag = True
                    elif i[0] == 'add':
                        for add in i[-1]:  # i[-1]增加的[('11orderByField', '3'),('dd', {'1': 2, '2': 33})]
                            exist_data.update({add[0]: add[1]})  # 在原有参数加上更新的内容
                            res_list.append(f"用例id {case.id}  增加参数{add[0]}:{add[1]}")
                        flag = True
            if flag:  # 说明有新增或者移除的
                req_data['single_body'] = exist_data
                serializer = CaseCodeSerializer(case, data=req_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                print(serializer.data["id"])
            else:  # 没有新增或者移除的
                res_list.append(f"用例id {case.id}  与接口id {req_data['id']}参数一致，不做改动")
    else:  # 用例里面没有该接口，直接保存
        req_data['single_body'] = req_data['params']  # api参数 params给到 single_body
        serializer = CaseCodeSerializer(data=req_data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        res_list.append(f"接口id {str(req_data['id'])} '生成用例: {str(serializer.data['id'])}")
        SwaggerApi.objects.filter(id=req_data['id']).update(status="有用例")
    case_result = {f"接口id {req_data['id']}": res_list} if res_list else {}

    return Response(data={"code": 10000, "msg": "操作成功", "data": case_result})


@api_view(['GET'])
def view_case_result(request, **kwargs):  # 查看单用例执行结果接口
    case_id = kwargs['pk']
    instances = CaseResult.objects.filter(case_id=case_id, case_type__in=[1, 11]).order_by('-run_time')
    if instances:
        serializer = CaseResultSerializer(instances[0])
        return Response({"code": 10000, "msg": "查看结果成功", "data": serializer.data})
    else:
        return Response({"code": 10000, "msg": "未找到该单用例执行结果"})


@api_view(['POST'])
def get_case(request):
    case_list = request.data.get("caseList")  # 获得选中 单用例的id列表
    case_group_list = request.data.get("caseGroupList")  # 获得选中 组合用例的id列表
    data = dict()
    if case_list:
        case_data = Case.objects.filter(id__in=case_list)
        serializer = CaseListSerializer(case_data, many=True)
        data.update({"case": serializer.data})
    if case_group_list:
        cases_data = CaseGroup.objects.filter(id__in=case_group_list)
        serializers = CaseGroupListSerializer(cases_data, many=True)
        data.update({"cases": serializers.data})

    return Response({"code": 10000, "msg": "查询成功", "data": data})


def get_xxl_job(job_id):
    data = xxjobMenu.objects.filter(id=job_id)
    if data:
        data1 = data[0]
