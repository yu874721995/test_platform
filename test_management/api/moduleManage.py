# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten

import json
import logging
import requests
from test_management import models
from django.http import HttpResponse
from test_management.common import json_request,request_verify
from django.core.paginator import Paginator
from test_management.common import DateEncoder,jwt_token
from django.db.models import Q

r = requests.session()
logger = logging.getLogger(__name__)

class moduleViewSet():

    @classmethod
    @request_verify('post',
        {'project_id':int,
        'name':str,
        'type':int}
    )
    def create(cls,request):
        id = json_request(request,'id',int,not_null=False,default=None)
        project_id = json_request(request,'project_id',int)
        name = json_request(request, 'name',not_null=False)
        server_env = json_request(request, 'server_env',default=None)
        if not server_env or server_env == 'None':
            server_env = '-'
        up_id = json_request(request, 'up_id',int,not_null=False,default=None)
        type = json_request(request, 'type', int)#1位一级，2为二级,3为三级
        master = json_request(request, 'master', int)
        dev_master = json_request(request, 'dev_master', int,not_null=False,default=1)
        creator = jwt_token(request)['username']
        user_id = jwt_token(request)['userId']
        if not master:
            master = user_id
        if not id:
            # up_name_exist = models.moduleMent.objects.filter(name=name, project_id=project_id).exists()
            # if up_name_exist:
            #     return HttpResponse(json.dumps({
            #         'code': 10005,
            #         'msg': '该模块已存在'
            #     }))
            pass
        else:
            id_exist = models.moduleMent.objects.filter(id=id).exists()
            if not id_exist:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '没有该模块'
                }))
            # up_name_exist = models.moduleMent.objects.filter(name=name, project_id=project_id).exclude(id=id).exists()
            # if up_name_exist:
            #     return HttpResponse(json.dumps({
            #         'code': 10005,
            #         'msg': '该模块已存在'
            #     }))
        if type != 1:
            if not up_id:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '下级分类必须选择一个上级分类'
                }))

        try:
            if id:
                models.moduleMent.objects.update_or_create(defaults={
                    'project_id':project_id,
                    'name': name,
                    'server_env': server_env,
                    'up_id': up_id,
                    'type': type,
                    'master':master,
                    'dev_master':dev_master,
                    'creator': creator
                },id=id)
            else:
                models.moduleMent.objects.create(**{
                    'project_id': project_id,
                    'name': name,
                    'server_env': server_env,
                    'up_id': up_id,
                    'type': type,
                    'master': master,
                    'dev_master': dev_master,
                    'creator': creator
                })
        except Exception as e:
            logger.error(str(e))
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '添加分类错误'
            }))
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    def list(self, request):
        page = json_request(request,'page',int,default=1)
        limit = json_request(request,'limit',int,default=20)
        module_name = json_request(request,'module_name',default=None,not_null=False)
        project_id = json_request(request,'project_id',default=None,not_null=False)
        master = json_request(request,'master',default=None,not_null=False)
        query = Q()
        if module_name:
            query &= Q(name__contains=module_name)
        if project_id:
            query &= Q(project_id=project_id)
        if master:
            query &= Q(master=master)

        up_datas = list(models.moduleMent.objects.filter(query,type=1).order_by('-create_time').values())
        dow_datas = list(models.moduleMent.objects.filter(query, type=2).order_by('-create_time').values())
        for dow_data in dow_datas:
            dow_data['children'] = list(models.moduleMent.objects.filter(query,type=3,up_id=dow_data['id']).order_by('-create_time').values())
        for up_data in up_datas:
            up_data['children'] = []
            for dow_data in dow_datas:
                if up_data['id'] == dow_data['up_id']:
                    up_data['children'].append(dow_data)
        p = Paginator(up_datas, limit)  # 实例化分页对象
        count = p.count
        logging.info('联调标签查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'items': result
        },cls=DateEncoder))

    @classmethod
    def delete(cls,request):
        id = json_request(request,'id',int,not_null=False)
        type = json_request(request,'type',int,not_null=False)
        id_exist = models.moduleMent.objects.filter(id=id).exists()
        if not id_exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '该模块不存在'
            }))
        try:
            if type == 1:
                models.moduleMent.objects.filter(id=id).update(status=2)
            else:
                models.moduleMent.objects.filter(id=id).update(status=1)
        except Exception as e:
            logger.error(str(e))
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '禁用模块失败'
            }))
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))



