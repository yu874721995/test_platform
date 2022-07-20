from django.urls import path
from test_tools.api.BKCI_tool import BkCiToolView
from test_tools.api.xxjob_tools import xxjob_toolesView

urlpatterns = [
    path(r"list", BkCiToolView.List),
    path(r"bkci_Callback", BkCiToolView.bkci_Callback),
    path(r"to_examine", BkCiToolView.to_examine),
    path(r"structure", BkCiToolView.structure),
    path(r"offline",BkCiToolView.offline),
    path(r"build_xxjob",xxjob_toolesView.build_xxjob),
    path(r"xxjob_list",xxjob_toolesView.xxjob_list),
    path(r"dev_seach_pre",BkCiToolView.dev_seach_pre),
    path(r"updateAssembly",BkCiToolView.updateAssembly),

]