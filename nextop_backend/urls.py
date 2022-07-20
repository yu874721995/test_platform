"""nextop_backend URL Configuration"""
from django.urls import path, include
from test_plant import views
from test_management import views
from test_plant import task
from test_tools import task
from django.conf.urls import re_path
from nextop_tapd.api import tapd
from nextop_tapd.api import ding

urlpatterns = [
    path('api/users/', include('user.urls')),
    path('api/api_case/', include('api_case.urls')),
    path('api/test_management/', include('test_management.urls')),
    path('api/test_plant/', include('test_plant.urls')),
    path('api/test_tapd/', include('nextop_tapd.urls')),
    path('api/test_tools/', include('test_tools.urls')),
    re_path('tapdMsgPush', tapd.tapdMsgPush),
    re_path('tapdMsgNewPush', tapd.tapdMsgNewPush),
    re_path('callback/dingding_msg', ding.ding_msg_callback),
    re_path('uploadDingdingMailList', tapd.upload_dingding_mail_list),
]
