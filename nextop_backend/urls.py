"""nextop_backend URL Configuration"""
import logging

from django.urls import path, include
from test_plant import views
from test_management import views,task
from test_plant import task
from test_tools import task,jenkins_task
from test_yunxiao import task
from django.conf.urls import re_path
from nextop_tapd.api import tapd
from nextop_tapd.api import ding
from test_tools.models import MockApiVersionModel
from test_tools.api.MockApi import MockApiVersionView
from middleware import free_url
from test_tools.api.ServiceMonitoring import ServiceMonitoring
from test_tools.api.jenkins_bkci_tool import JenKinsBkCiToolView

urlpatterns = [
    path('api/users/', include('user.urls')),
    path('api/api_case/', include('api_case.urls')),
    path('api/test_management/', include('test_management.urls')),
    path('api/test_plant/', include('test_plant.urls')),
    path('api/test_tapd/', include('nextop_tapd.urls')),
    path('api/test_tools/', include('test_tools.urls')),
    path('api/test_yunxiao/', include('test_yunxiao.urls')),
    path('api/test_case/', include('test_case.urls')),
    re_path('test-platform/tapdMsgPush', tapd.tapdMsgPush),
    re_path('test-platform/tapdMsgNewPush', tapd.tapdMsgNewPush),
    re_path('test-platform/callback/dingding_msg', ding.ding_msg_callback),
    re_path('test-platform/uploadDingdingMailList', tapd.upload_dingding_mail_list),
    path(r"test-platform/api/test_tools/serviceMonitorWebhook", ServiceMonitoring.serviceMonitorWebhook),
    path(r"test-platform/api/test_tools/bkci_Callback",JenKinsBkCiToolView.bkci_Callback)
]
mock_query = MockApiVersionModel.objects.filter(status=1,is_delete=0)
for mock in mock_query:
    url = mock.url[1:] if mock.url[0] == '/' else mock.url
    urlpatterns.append(
        path(r"{}".format(url),MockApiVersionView.MockInterFace)
    )
    free_url.append(mock.url)
    logging.info('添加mock路由成功：{}'.format(url))
