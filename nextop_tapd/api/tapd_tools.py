# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten

import json
import logging
import requests
from test_management import models
from django.http import HttpResponse
from test_management.common import json_request, request_verify
from test_management.common import  jwt_token
from nextop_tapd.common import create_bug
from api_case.models import MitData

r = requests.session()
logger = logging.getLogger(__name__)

class Tapd_ToolsView():

    @classmethod
    @request_verify('post',{'project_id':str,'title':str,'description':str,'priority':str,'severity':str,'owner':str})
    def createBug(cls,request):
        username = jwt_token(request)['username']
        cookie_exsit = models.system_config.objects.filter(name=username+'_tapd_cookie').exists()
        if not cookie_exsit:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '未找到name为{}_tapd_cookie的基础配置信息，请先配置完成'.format(username)
            }))
        mit_id = json_request(request,'mit_id',int,not_null=False,default=None)
        cookie = models.system_config.objects.get(name=username+'_tapd_cookie').ext
        project_id = json_request(request,'project_id',str,not_null=False,default=None)
        title = json_request(request, 'title', str, not_null=False, default=None)
        description = json_request(request, 'description', str, not_null=False, default=None)
        priority = json_request(request, 'priority', str, not_null=False, default=None)
        severity = json_request(request, 'severity', str, not_null=False, default=None)
        owner = json_request(request, 'owner', str, not_null=False, default=None)
        if create_bug(project_id,title,description,priority,severity,owner,cookie):
            MitData.objects.filter(id=mit_id).update(is_bug=2)
            return HttpResponse(json.dumps({
                'code':10000,
                'msg':'创建成功'
            }))
        else:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '创建失败'
            }))
