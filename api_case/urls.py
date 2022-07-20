#!/usr/bin/python
# encoding=utf-8
from django.urls import path
from api_case.views import case, cases, run, mit_case_data, swagger, report

urlpatterns = [
    # ------------------单接口用例模块接口------------------
    path(r"case", case.CaseViewSet.as_view({
        "get": "list",    # 用例列表展示
        "post": "create"  # 添加单个用例
    })),
    path(r"case/page", case.case_page),  # 用例列表展示, post请求
    path(r"case/<int:pk>", case.CaseViewSet.as_view({
        "get": "retrieve",  # 展示单个用例
        "put": "update",    # 更新用例
        "delete": "destroy"  # 删除用例
    })),
    path(r"case/<int:pk>/result", case.view_case_result),  # 查看用例结果
    path(r"case/<int:pk>/run", run.run_case),  # 运行用例

    path(r"case/convertCase", case.convert),  # mitmproxy 转用例
    path(r"case/convertCase/batch", case.batch_convert),  # mitmproxy 批量转用例接口
    path(r"case/convertApi", case.swagger_convert),  # swagger api转用例
    # ------------------组合用例接口------------------
    path(r"cases", cases.CaseGroupViewSet.as_view({
        "get": "list",
        "post": "create"
    })),
    path(r"cases/page", cases.cases_page),  # 用例列表展示
    path(r"cases/<int:pk>", cases.CaseGroupViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "delete": "destroy"
    })),
    path(r"cases/<int:pk>/result", cases.view_case_result),  # 查看组合用例结果
    # ------------------获取用例数据，报告数据接口------------------
    path(r"case/get", case.get_case),  # 获取用例数据，在测试计划编辑里面需要此接口

    # path(r"cases/<int:pk>/copy", case.copy_case),  # 复制用例
    path(r"cases/<int:pk>/run", run.run_case),     # 运行用例

    path(r"case/batch_run", run.run_batch_case),    # 批量运行单接口用例
    path(r"cases/batch_run", run.run_batch_case),   # 批量运行组合用例

    # ------------------mitmproxy获取的数据 增删改查------------------
    path(r"mitdata", mit_case_data.MitDataViewSet.as_view({
        "get": "list"
    })),
    path(r"mitdata/<int:pk>", mit_case_data.MitDataViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "delete": "destroy"
    })),

    # ------------------swagger获取的数据 增删改查------------------
    path(r"swagger", swagger.SwaggerViewSet.as_view({
        "get": "list",
        "post": "create"  # 批量查询接口变更，有变更就写入到数据库
    })),
    path(r"swagger/<int:pk>", swagger.SwaggerViewSet.as_view({
        "get": "retrieve",
        "put": "update",
        "delete": "destroy"
    })),
    path(r"swagger/sync", swagger.sync_swagger),  # swagger同步api数据接口

    # ------------------测试报告获取的数据 查------------------
    path(r"report", report.TestReportViewSet.as_view({
        "get": "list"
    })),
    path(r"report/detail", report.view_case_report),  # 查看报告详情
]
