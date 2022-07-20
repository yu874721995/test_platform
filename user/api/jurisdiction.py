# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :jurisdiction.py
# @Time      :2022/6/15 17:55
# @Author    :Careslten

import json
import logging
from django.http import HttpResponse
from django.core.paginator import Paginator
from test_management.common import json_request, DateEncoder, jwt_token, request_verify,AuthJurisdiction
from user.models import Jurisdiction, Role,Role_Jurisdiction
from django.db import transaction
from django.db.models import Q

logger = logging.getLogger(__name__)


class JurisdictionView():

    @classmethod
    @request_verify('post', check_params={'page': int, 'limit': int})
    def list(cls, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=20)
        querys = Jurisdiction.objects.filter(status=1,level=1).values().order_by('id')
        datas = []
        for query in querys:
            two_datas = []
            twos = list(Jurisdiction.objects.filter(status=1,up_id=query['id']).values())
            for two in twos:
                three_datas = []
                threes = list(Jurisdiction.objects.filter(status=1,up_id=two['id']).values())
                for three in threes:
                    fours = list(Jurisdiction.objects.filter(status=1,up_id=three['id']).values())
                    three['children'] = fours
                    three_datas.append(three)
                two['children'] = three_datas
                two_datas.append(two)
            query['children'] = two_datas
            datas.append(query)
        p = Paginator(datas, limit)  # 实例化分页对象
        count = p.count
        logging.info('定时任务查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'data': result
        }, cls=DateEncoder))

    @classmethod
    @request_verify('post', check_params={'page': int, 'limit': int})
    def allList(cls, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=20)
        querys = Jurisdiction.objects.filter(status=1).values().order_by('-id')
        p = Paginator(tuple(querys), limit)  # 实例化分页对象
        count = p.count
        logging.info('定时任务查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'data': result
        }, cls=DateEncoder))

    @classmethod
    @request_verify('post', {'name': str,'level': int,'title':str}, { 'up_id': int,'path': str})
    def create(cls, request):
        name = json_request(request, 'name', str, not_null=False, default=None)
        path = json_request(request, 'path', str, not_null=False, default=None)
        title = json_request(request, 'title', str, not_null=False, default=None)
        level = json_request(request, 'level', int, default=None)
        up_id = json_request(request, 'up_id', int, default=None)
        data = {
            'name': name,
            'path': path,
            'title':title,
            'level': level,
            'up_id': up_id
        }
        if level and level !=4 and not path:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '非按钮权限时菜单路径不能为空'
            }))
        pathExist = Jurisdiction.objects.filter(path=path, status=1).exists()
        if pathExist and path != "" and path:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': 'path重复'
            }))
        Jurisdiction.objects.create(**data)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    @request_verify('post', {'jurisdiction_id': int, 'name': str,'title':str},
                    {'path': str})
    def update(cls, request):
        jurisdiction_id = json_request(request, 'jurisdiction_id', int, default=None)
        name = json_request(request, 'name', str, not_null=False, default=None)
        path = json_request(request, 'path', str, not_null=False, default=None)
        title = json_request(request, 'title', str, not_null=False, default=None)
        if not Jurisdiction.objects.filter(id=jurisdiction_id).exists():
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '权限id不存在'
            }))
        level = Jurisdiction.objects.get(id=jurisdiction_id).level
        if level and level !=4 and not path:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '非按钮权限时菜单路径不能为空'
            }))
        if path:
            pathExist = Jurisdiction.objects.filter(path=path, status=1).exclude(id=jurisdiction_id).exists()
            if pathExist:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': 'path重复'
                }))
        Jurisdiction.objects.filter(id=jurisdiction_id).update(name=name,path=path,title=title)  # 修改权限
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    @request_verify('post', {'jurisdiction_id': int})
    def delete(cls, request):
        jurisdiction_id = json_request(request, 'jurisdiction_id', int, default=None)
        idExist = Jurisdiction.objects.filter(id=jurisdiction_id).exists()
        if not idExist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '权限不存在'
            }))
        Jurisdiction.objects.filter(id=jurisdiction_id).update(status=2)
        Role_Jurisdiction.objects.filter(Jurisdiction_id=jurisdiction_id).delete()
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))
