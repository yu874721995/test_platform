# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten


from django.urls import path
from nextop_tapd.api.Tapd_project_conf import tapd_project_conf
from nextop_tapd.api.Tapd_project_bugStatistics import tapd_project_bugStatistics
from nextop_tapd.api.tapd_tools import Tapd_ToolsView

urlpatterns = [
    # 测试管理路由
    path(r"tapdConfList", tapd_project_conf.page),
    path(r"createTapdConf", tapd_project_conf.create),
    path(r"deleteTapdConf", tapd_project_conf.delete),
    path(r"updateTapdConf", tapd_project_conf.update),
    path(r"test_to_msg", tapd_project_conf.excupt),
    path(r"demandStatus",tapd_project_conf.tapd_project_demandStatus),
    path(r"AllDemandStatus",tapd_project_conf.statsu_page),
    path(r"groupList",tapd_project_bugStatistics.groupList),
    path(r"updateNow",tapd_project_bugStatistics.update_now),
    path(r"plant_detail",tapd_project_bugStatistics.detail),
    path(r"createBug",Tapd_ToolsView.createBug),
]
