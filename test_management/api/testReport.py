# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten

import json
import logging
import requests
from django.http import HttpResponse
from test_management.common import json_request
from django.core.paginator import Paginator
from test_management.common import DateEncoder
from api_case import models as case_model

r = requests.session()
logger = logging.getLogger(__name__)

class TestReportViewSet():

    @classmethod
    def list(cls,request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=20)
        querys = case_model.CaseResult.objects.filter().values()
        p = Paginator(tuple(querys), limit)
        count = p.count
        logging.info('测试报告查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count, 'page': page, 'code': 10000, 'items': result
        }, cls=DateEncoder))
