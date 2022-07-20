# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten


from django.urls import path
from test_management.api.EnvManagement import EnvListSet
from test_management.api.ProjectManagement import ProjectListSet,TapdProjectListSet
from test_management.api.AccountManagent import AccountSetView
from test_management.api.moduleManage import moduleViewSet
from test_management.api.testReport import TestReportViewSet
from test_management.api.systemConfig import SystemConfig

urlpatterns = [
    # 测试管理路由
    path(r"envlist", EnvListSet.list),
    path(r"mail_list", AccountSetView.mail_list),
    path(r"selectEnvlist", EnvListSet.selectList),
    path(r"setCommon",EnvListSet.setCommon),
    path(r"setNoCommon",EnvListSet.setNoCommon),
    path(r"prolist", TapdProjectListSet.list),
    path(r"createAccount", AccountSetView.create),
    path(r"deleteAccount", AccountSetView.delete),
    path(r"updateAccount", AccountSetView.update),
    path(r"createPro",ProjectListSet.createProject),
    path(r"proList",ProjectListSet.proList),
    path(r"AccountList", AccountSetView.pagelist),
    path(r"createModule", moduleViewSet.create),
    path(r"moduleList", moduleViewSet.list),
    path(r"typeModule", moduleViewSet.delete),
    path(r"testReport",TestReportViewSet.list),
    path(r"checkAccount",AccountSetView.checkAccount),
    path(r"CreateConf",SystemConfig.create),
    path(r"ConfPage",SystemConfig.page),
    path(r"tapd_project_init",TapdProjectListSet.init),

]
