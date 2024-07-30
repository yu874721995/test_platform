from django.urls import path,re_path
from test_tools.api.BKCI_tool import BkCiToolView
from test_tools.api.jenkins_bkci_tool import JenKinsBkCiToolView
from test_tools.api.xxjob_tools import xxjob_toolesView
from test_tools.api.all_tool import AllToolView,dingtalk
from test_tools.api.DataComparison import DataComparisonView
from test_tools.api.sqlTreasureBox import TreasureBox
from test_tools.api.MockApi import MockApiView,MockApiVersionView
from test_tools.api.JacocoDiffView import JacocoDiffView


urlpatterns = [
    path(r"list", JenKinsBkCiToolView.List),
    path(r"bkci_Callback", JenKinsBkCiToolView.bkci_Callback),
    path(r"to_examine", JenKinsBkCiToolView.to_examine),
    path(r"structure", JenKinsBkCiToolView.structure),
    path(r"get_examine_result", JenKinsBkCiToolView.get_examine_result),
    path(r"build_xxjob", xxjob_toolesView.build_xxjob),
    path(r"xxjob_list", xxjob_toolesView.xxjob_list),
    path(r"dev_seach_pre", JenKinsBkCiToolView.dev_seach_pre),
    path(r"updateAssembly", JenKinsBkCiToolView.updateAssembly),
    path(r"get_servicename_list", JenKinsBkCiToolView.get_servicename_list),
    path(r"ContainerListNumber", AllToolView.ContainerListNumber),
    path(r"DataComparisonList", DataComparisonView.List),
    path(r"DataComparisonCreate", DataComparisonView.Create),
    path(r"UpdateDataComparison", DataComparisonView.Update),
    path(r"DeleteDataComparison", DataComparisonView.Delete),
    path(r"BuildDataComparison", DataComparisonView.Build),
    path(r"data_executions_list", DataComparisonView.data_executions_list),
    path(r"TreasureBoxList", TreasureBox.List),
    path(r"TreasureBoxCreate", TreasureBox.Create),
    path(r"TreasureBoxUpdate", TreasureBox.Update),
    path(r"TreasureBoxDelete", TreasureBox.Delete),
    path(r"TreasureBoxBuild", TreasureBox.Build),
    path(r"TreasureBoxConfigList", TreasureBox.ConfigList),
    path(r"MockApiViewList",MockApiView.List),
    path(r"MockApiViewCreate",MockApiView.Create),
    path(r"MockApiViewUpdate",MockApiView.Update),
    path(r"MockApiViewDelete",MockApiView.Delete),
    path(r"MockApiViewupdateStatus",MockApiView.updateStatus),
    path(r"MockApiVersionViewList",MockApiVersionView.List),
    path(r"MockApiVersionViewCreate",MockApiVersionView.Create),
    path(r"MockApiVersionViewUpdate",MockApiVersionView.Update),
    path(r"MockApiVersionViewDelete",MockApiVersionView.Delete),
    path(r"MockApiVersionViewupdateStatus",MockApiVersionView.updateStatus),
    path(r"jacoco_build",JacocoDiffView.build),
    path(r"get_last_commitid",JacocoDiffView.get_last_commitid),
    path(r"jacoco_build_history_list",JacocoDiffView.jacoco_build_history_list),
    path(r"dingtalk",dingtalk),
    path(r"checkCommitDiff",JenKinsBkCiToolView.checkCommitDiff),
    path(r"uat_service_list",JenKinsBkCiToolView.uat_service_list),
    path(r"XmindToTestCase",AllToolView.uploadXmind),
    path(r"buildHistoryList",JenKinsBkCiToolView.buildHistoryList),
    path(r"addBuildHistoryReason",JenKinsBkCiToolView.addBuildHistoryReason),
    path(r"compatibleAssemblyList",JenKinsBkCiToolView.compatibleAssemblyList),
    path(r"uploadBuildHistroy",JenKinsBkCiToolView.uploadBuildHistroy),
    path(r"switchBuildSwatch",JenKinsBkCiToolView.switchBuildSwatch),
    path(r"createServiceErrorBug",AllToolView.createServiceErrorBug)

]
