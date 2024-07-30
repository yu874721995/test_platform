# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten

import json
import logging
from django.http import HttpResponse
from django.core.paginator import Paginator
from test_management import models
from django.db.models import Q
from test_management.common import json_request, DateEncoder, jwt_token

logger = logging.getLogger(__name__)


class EnvListSet():
    '''测试管理-环境标签列表'''

    @classmethod
    def list(self, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=20)
        env_name = json_request(request, 'env_name', default=None, not_null=False)
        server_env = json_request(request, 'server_env', default=None, not_null=False)
        label_name = json_request(request, 'label_name', default=None, not_null=False)
        userId = jwt_token(request)['userId']
        query = Q(status=1)
        if env_name:
            query &= Q(env_name=env_name)
        if server_env:
            query &= Q(server_env__contains=server_env)
        if label_name:
            query &= Q(lable_name__contains=label_name)
        # list所有标签
        datas = list(models.envList.objects.filter(query).order_by('-env_name').values())
        # # 异步更新环境信息
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # task = [asyncio.ensure_future(update_pro())]
        # loop.run_until_complete(asyncio.wait(task))
        # loop.close()
        # 用户设为常用的标签
        commonEnvId = [x['env_id'] for x in models.envCommon.objects.filter(user_id=userId, status=1).values()]
        new_data = []
        for data in datas:
            if data['id'] in commonEnvId:
                data['common'] = 2
            else:
                data['common'] = 1
            new_data.append(data)
        new_data = sorted(new_data, key=lambda data: data['common'], reverse=True)
        p = Paginator(new_data, limit)  # 实例化分页对象
        count = p.count
        logging.info('联调标签查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'items': result
        }, cls=DateEncoder))

    @classmethod
    def setCommon(cls, request):
        env_id = json_request(request, 'env_id', int)
        exist = models.envList.objects.filter(id=env_id).exists()
        if not exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '标签不存在'
            }, cls=DateEncoder))
        userId = jwt_token(request)['userId']
        exists = models.envCommon.objects.filter(env_id=env_id, user_id=userId, status=1).exists()
        if exists:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '标签已设为常用'
            }, cls=DateEncoder))
        try:
            models.envCommon.objects.create(**{
                'env_id': env_id,
                'user_id': userId
            })
            return HttpResponse(json.dumps({
                'code': 10000,
                'msg': '操作成功'
            }, cls=DateEncoder))
        except Exception as e:
            logger.error(str(e))
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '添加失败'
            }, cls=DateEncoder))

    @classmethod
    def setNoCommon(cls, request):
        env_id = json_request(request, 'env_id', int)
        exist = models.envList.objects.filter(id=env_id, status=1).exists()
        if not exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '标签不存在'
            }, cls=DateEncoder))
        userId = jwt_token(request)['userId']
        exists = models.envCommon.objects.filter(env_id=env_id, user_id=userId, status=1).exists()
        if not exists:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '标签并未设为常用'
            }, cls=DateEncoder))
        try:
            models.envCommon.objects.filter(env_id=env_id, user_id=userId, status=1).update(status=2)
            return HttpResponse(json.dumps({
                'code': 10000,
                'msg': '操作成功'
            }, cls=DateEncoder))
        except Exception as e:
            logger.error(str(e))
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '操作失败'
            }, cls=DateEncoder))

    @classmethod
    def selectList(cls, request):
        userId = jwt_token(request)['userId']
        querys = list(models.envList.objects.filter(status=1).order_by('-env_name').values())
        commonEnvId = [x['env_id'] for x in models.envCommon.objects.filter(user_id=userId, status=1).values()]
        new_data = []
        for query in querys:
            if query['id'] in commonEnvId:
                query['common'] = 2
            else:
                query['common'] = 1
            new_data.append(query)
        datas = [{
            'id': 1,
            'lable_name': '常用',
            'server_env': '常用',
            'children': []
        }, {
            'id': 2,
            'lable_name': "联调环境",
            'server_env': '联调环境',
            'children': []
        },
            {
                'id': 3,
                'lable_name': "预发环境",
                'server_env': '预发环境',
                'children': []
            },
        ]
        for query in new_data:
            if query['common'] == 2:
                datas[0]['children'].append(query)
            if query['env_name'] == 'daily':
                datas[1]['children'].append(query)
                continue
            if query['env_name'] == 'nextop-pre':
                datas[2]['children'].append(query)
                continue
        # # 异步更新环境信息
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # task = [asyncio.ensure_future(update_pro())]
        # loop.run_until_complete(asyncio.wait(task))
        # loop.close()
        # 用户设为常用的标签

        return HttpResponse(json.dumps({
            'code': 10000,
            'items': datas
        }, cls=DateEncoder))


