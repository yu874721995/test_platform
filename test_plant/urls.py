# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten


from django.urls import path
from test_plant.api.ScheduledTaskList import ScheduledTaskListSet
from test_plant.api.TestPlant import TestPlantView
from test_plant.api.binlogToTask import work

urlpatterns = [
    # 任务管理路由
    path(r"ScheduledTaskList", ScheduledTaskListSet.list),
    path(r"create_job", ScheduledTaskListSet.create),
    path(r"update_job", ScheduledTaskListSet.update),
    path(r"ScheduledTaskExcuList", ScheduledTaskListSet.job_list),
    path(r"delete_job", ScheduledTaskListSet.delete),
    path(r"execution_one_job", ScheduledTaskListSet.execution_one),
    path(r"job_executions_list", ScheduledTaskListSet.job_executions_list),

    path(r"create_test_plant", TestPlantView.create),
    path(r"update_test_plant", TestPlantView.update),
    path(r"test_plant_list", TestPlantView.plant_list),
    path(r"test_plant_excu_list", TestPlantView.plant_executions_list),
    path(r"delete_plant", TestPlantView.delete),
    path(r"PlantCaseList", TestPlantView.PlantCaseList),
    path(r"checkReportStatus",TestPlantView.checkReportStatus),
    path(r"execution_one_plant", TestPlantView.execution_one),



]
# work()