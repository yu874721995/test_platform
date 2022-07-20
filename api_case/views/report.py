# coding=utf-8
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api_case.serializers import CaseTestReportListSerializer, CaseResultSerializer
from utils.pagination import CustomPagination
from api_case.models import CaseTestReport, CaseResult


class TestReportViewSet(ModelViewSet):
    queryset = CaseTestReport.objects.all()
    serializer_class = CaseTestReportListSerializer

    def list(self, request, *args, **kwargs):
        query = Q()
        report_name = request.GET.get("name")
        if report_name:  # 如果传了报告名称
            query &= Q(report_name__icontains=report_name)
        create_user = request.GET.get("create_user")
        if create_user:  # 如果传了接口路径
            query &= Q(creator_nickname__icontains=create_user)
        queryset = CaseTestReport.objects.filter(query).order_by('-id')  # 按照用例id倒序
        cp = CustomPagination()  # 排序、分页处理
        page = cp.paginate_queryset(queryset, request=request)
        size = cp.get_page_size(request)
        if page is not None:
            serializer = CaseTestReportListSerializer(page, many=True)
            data = cp.get_paginated_response(serializer.data)
            data.update({'size': size})
            return Response(data)


@api_view(['POST'])
def view_case_report(request):  # 查看组合用例结果表
    report_id = request.data.get("report_id")
    instances = CaseTestReport.objects.filter(id=report_id)
    serializer = CaseTestReportListSerializer(instances[0])
    report_data = serializer.data
    report_name = report_data.get('report_name')
    # "case_type运行类型：1.单用例，2.组合用例 11.批量单用例，22.批量组合用例 3.计划单用例，4.计划组合用例"
    if '【批量执行】_' in report_name:  # 批量执行的结果类型是11， 22
        case_result = CaseResult.objects.filter(
            case_id__in=report_data.get('case_id'), case_type=11,
            run_user_nickname=report_data.get('run_user_nickname'))
        case_group_result = CaseResult.objects.filter(
            case_id__in=report_data.get('case_group_id'), case_type=22,
            run_user_nickname=report_data.get('run_user_nickname'))
    else:  # 非批量执行的结果
        case_result = CaseResult.objects.filter(
            case_id__in=report_data.get('case_id'), case_type=3,
            run_user_nickname=report_data.get('run_user_nickname'))
        case_group_result = CaseResult.objects.filter(
            case_id__in=report_data.get('case_group_id'), case_type=4,
            run_user_nickname=report_data.get('run_user_nickname'))
    for i in case_result:
        print("单用例", i.case_id)
    case_result_data = CaseResultSerializer(case_result, many=True)
    case_group_result_data = CaseResultSerializer(case_group_result, many=True)
    # for j in case_group_result:
    #     print("组合用例", j.case_id)
    report_data.update({'case_result': case_result_data.data})
    report_data.update({'case_group_result': case_group_result_data.data})
    return Response({"code": 10000, "msg": "查看报告成功", "data": report_data})
