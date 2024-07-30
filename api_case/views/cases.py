# coding=utf-8
import json
import time
from collections import OrderedDict

# from channels.generic.websocket import JsonWebsocketConsumer
# from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api_case.models import Case, CaseGroup, CaseResult
from api_case.serializers import CaseGroupSerializer, CaseGroupListSerializer, CaseResultSerializer
from test_management.models import envList, ErpAccount
from api_case.create_project.sample_code import combined_case, generated_code
from utils.api_response import MyResponse, jwt_token
from utils.pagination import CustomPagination


def get_code(obj):
    case_id, req_method, url = obj.id, obj.req_method, obj.url
    single_body, pre_sql, end_sql = obj.single_body, obj.pre_sql, obj.end_sql
    assert_res, group_body, extract_param = obj.assert_res, obj.group_body, obj.extract_param
    # 生成code, 先判断是否有 组合参数group_body，有的话就生成组合参数用的 group_code
    code = generated_code(case_id=case_id, req_method=req_method, url=url, assert_res=assert_res,
                          body=single_body, pre_sql=pre_sql, end_sql=end_sql,
                          extract_param=extract_param)
    Case.objects.filter(id=case_id).update(code=code)
    if group_body:
        group_code = generated_code(case_id=case_id, req_method=req_method,
                                    url=url, assert_res=pre_sql,
                                    body=group_body, pre_sql=pre_sql,
                                    end_sql=end_sql, extract_param=extract_param)
        Case.objects.filter(id=case_id).update(group_code=group_code)
    else:  # 没有组合参数时，把单参数变成组合参数
        Case.objects.filter(id=case_id).update(group_code=code)


@api_view(['POST'])
def cases_page(request):
    query = Q()
    project_id = request.data.get("projectId")
    if project_id:  # 如果传了用例id
        query &= Q(project_id=project_id)
    create_user = request.data.get("create_user")
    if create_user:  # 如果传了接口路径
        query &= Q(creator_nickname__icontains=create_user)
    name = request.data.get('name')
    if name:
        query &= Q(name__icontains=name)
    modules = request.data.get("module")
    if modules:  # 如果传模块[[15, 90], [1, 3]] <class 'list'>
        query_m = Q()
        for module in modules:
            if len(module) == 1:
                query_m |= Q(module__icontains='[' + str(module[0]) + ',')
            else:
                query_m |= Q(module__icontains=module)
        query &= query_m

    queryset = CaseGroup.objects.filter(query).order_by('-id')  # 按照用例id倒序
    p = Paginator(queryset, request.data['size'])  # 分页
    page = request.data['page']
    size = request.data['size']
    total_page = p.num_pages
    total_num = p.count  # 总页数
    case_data = [] if page not in p.page_range else p.page(page).object_list
    serializer = CaseGroupListSerializer(case_data, many=True)
    data = OrderedDict({"code": 10000, "msg": "查询成功",
                        'page': page,  # 当前页数
                        'size': size,  # 每页展示数据的数量
                        'totalNum': total_num,  # 总页数
                        'totalPage': total_page,  # 总数据数量
                        'data': serializer.data})
    return Response(data)


class CaseGroupViewSet(ModelViewSet):
    queryset = CaseGroup.objects.all()
    serializer_class = CaseGroupSerializer

    def list(self, request, *args, **kwargs):
        # project_id = request.GET.get('projectId')
        query = Q()
        project_id = request.GET.get("projectId")
        if project_id:  # 如果传了用例id
            query &= Q(id=project_id)
        create_user = request.GET.get("create_user")
        if create_user:  # 如果传了接口路径
            query &= Q(creator_nickname__icontains=create_user)
        module = request.GET.get("module")
        if module:  # 如果传模块id "1,3"
            module = module.strip("'").strip('"').split(',')
            module = list(map(int, module))  # 转成 list 后是带空格的字符串 "1, 3"
            query &= Q(module__icontains=str(module))
        name = request.GET.get('name')
        if name:
            query &= Q(name__icontains=name)
        queryset = CaseGroup.objects.filter(query).order_by('-id')  # 按照用例id倒序
        cp = CustomPagination()
        page = cp.paginate_queryset(queryset, request=request)
        size = cp.get_page_size(request)
        if page is not None:
            serializer = CaseGroupListSerializer(page, many=True)
            data = cp.get_paginated_response(serializer.data)
            data.update({'size': size})
            return Response(data)

    def create(self, request, *args, **kwargs):
        user_name = jwt_token(request)['username']
        request.data['creator_nickname'] = user_name
        request.data['updated_nickname'] = ''
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # 通过用例id列表查询到用例id对应的code_list,调用组合代码的方法combined_case返回组合后的 用例代码
        case_list = request.data.get("caseId_list")
        code_list = [Case.objects.filter(id=i)[0].group_code for i in case_list]
        # code_list = Case.objects.filter(id__in=case_list).values('group_code')  # 使用group_code
        combined_code = combined_case(code_list)
        CaseGroup.objects.filter(id=serializer.data['id']).update(code=combined_code)
        return Response(data={"code": 10000, "msg": "组合用例创建成功"},
                        status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        cases_id = kwargs["pk"]
        user_name = jwt_token(request)['username']
        request.data['updated_nickname'] = user_name
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        # 通过用例id列表查询到用例id对应的code_list,调用组合代码的方法combined_case返回组合后的 用例代码
        case_list = request.data.get("caseId_list")
        if case_list:
            code_list = [Case.objects.filter(id=i)[0].group_code for i in case_list]
        else:
            return Response(data={"code": 50000, "msg": "请选择用例"})
        combined_code = combined_case(code_list)
        # 使用filter().update更新 组合用例代码
        CaseGroup.objects.filter(id=serializer.data['id']).update(code=combined_code)
        return MyResponse(msg="组合用例修改成功")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = CaseGroupListSerializer(instance)
        return MyResponse(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return MyResponse(msg="组合用例删除成功")

    def perform_destroy(self, instance):
        instance.delete()


@api_view(['GET'])
def view_case_result(request, **kwargs):  # 查看组合用例结果表
    case_id = kwargs['pk']
    instances = CaseResult.objects.filter(case_id=case_id, case_type__in=[2, 22]).order_by('-run_time')
    serializer = CaseResultSerializer(instances[0])
    return Response({"code": 10000, "msg": "查看结果成功", "data": serializer.data})
