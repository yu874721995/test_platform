# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten


import json
import logging
import requests
from test_management import models
from django.http import HttpResponse
from django.db import transaction
from test_plant.common import add_job
from test_management.common import json_request, request_verify
from django.core.paginator import Paginator
from test_management.common import DateEncoder, jwt_token
from django.db.models import Q
from nextop_tapd import models as tapd_models
from utils.tapdTemplate import TapdTemplate
from utils.ding_talk import DingDingSend
from django.utils import timezone
import datetime

r = requests.session()
logger = logging.getLogger(__name__)


class tapd_project_middle_conf():

    @classmethod
    @request_verify('post', {'tapd_project_id': int,'push_time':dict},
                    {'demand_status': list, 'middle_status': list,'times':int, 'users': list})
    def create(cls, request):
        tapd_project_id = json_request(request, 'tapd_project_id')
        iteration_id = json_request(request, 'iteration_id')  # 迭代id
        demand_status = json_request(request,'demand_status',list)
        middle_status = json_request(request,'middle_status',list)
        times = json_request(request,'times',int)
        push_time = json_request(request,'push_time',dict)
        webhook_url = json_request(request, 'webhook_url')
        users = json_request(request, 'users', list)
        creator = jwt_token(request)['username']
        if not webhook_url and not users:
            return HttpResponse(json.dumps({'code': 10005, 'msg': '推送人和webhook地址必须填写一其中个'}))
        with transaction.atomic() as f:
            tapd_models.tapd_project_middle_conf.objects.create(
                **{
                    'tapd_project_id': tapd_project_id,
                    'iteration_id': iteration_id,
                    'demand_status': demand_status,
                    'middle_status': middle_status,
                    'times': times,
                    'push_time': push_time,
                    'webhook_url': webhook_url,
                    'users': users,
                    'creator': creator
                }
            )
            add_job()

        return HttpResponse(json.dumps({'code': 10000, 'msg': '添加成功'}))

    @classmethod
    def page(cls, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=20)
        tapd_project_id = json_request(request, 'tapd_project_id', not_null=False, default=None)
        creator = json_request(request, 'creator', not_null=False, default=None)
        query = Q(status=1)
        if tapd_project_id:
            query &= Q(tapd_project_id=tapd_project_id)
        if creator:
            query &= Q(creator__icontains=creator)
        querys = tapd_models.tapd_project_conf.objects.filter(status=1).values().order_by('-create_time')
        datas = []
        if querys:
            for query in querys:
                if query['users']:
                    query['users'] = eval(query['users'])
                if query['demand_before_status']:
                    query['demand_before_status'] = eval(query['demand_before_status'])
                if query['demand_after_status']:
                    query['demand_after_status'] = eval(query['demand_after_status'])
                datas.append(query)
        p = Paginator(datas, limit)
        count = p.count
        logging.info('查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count, 'page': page, 'code': 10000, 'data': result
        }, cls=DateEncoder))

    @classmethod
    def statsu_page(cls, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=20)
        querys = models.system_config.objects.filter(name__contains='demand_status_').values()
        datas = []
        if querys:
            for query in querys:
                data = {}
                data['tapd_project_id'] = query['name'].split('_')[-1]
                data['statusData'] = eval(query['ext'])
                data['statusData']['newDemand'] = '新增需求'
                datas.append(data)
        p = Paginator(datas, limit)
        count = p.count
        logging.info('查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count, 'page': page, 'code': 10000, 'data': result
        }, cls=DateEncoder))

    @classmethod
    @request_verify('post', {'id': int, 'tapd_project_id': int},
                    {'demand_before_status': list, 'demand_after_status': list, 'users': list})
    def update(cls, request):
        id = json_request(request, 'id')
        tapd_project_id = json_request(request, 'tapd_project_id')
        iteration_id = json_request(request, 'iteration_id')  # 迭代id
        demand_before_status = json_request(request, 'demand_before_status', list)  # 为空代表任意状态流转至after都push
        demand_after_status = json_request(request, 'demand_after_status',
                                           list)  # 为空代表before状态流转至任意状态都push 都不填则任意状态流转至任意状态都推送
        start_time = json_request(request, 'start_time', not_null=False)  # 不填则不限制
        end_time = json_request(request, 'end_time', not_null=False)  # 不填则不限制
        webhook_url = json_request(request, 'webhook_url')
        if start_time:
            start_time = timezone.datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(
                hours=8)  # 前端传的UTC时间。。。
        if end_time:
            end_time = timezone.datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(
                hours=8)  # 前端传的UTC时间。。。
        users = json_request(request, 'users', list)
        exist = tapd_models.tapd_project_conf.objects.filter(id=id, status=1).exists()
        if not exist:
            return HttpResponse(json.dumps({'code': 10005, 'msg': '该记录不存在或已被删除'}))
        if not webhook_url and not users:
            return HttpResponse(json.dumps({'code': 10005, 'msg': '推送人和webhook地址必须填写一其中个'}))
        try:
            tapd_models.tapd_project_conf.objects.update_or_create(defaults={
                'tapd_project_id': tapd_project_id,
                'iteration_id': iteration_id,
                'demand_before_status': demand_before_status,
                'demand_after_status': demand_after_status,
                'start_time': start_time,
                'end_time': end_time,
                'webhook_url': webhook_url,
                'users': users,
            }, id=id)
        except Exception as e:
            logger.error('编辑失败，失败原因：{}'.format(str(e)))
            return HttpResponse(json.dumps({'code': 10005, 'msg': '更新失败'}))
        return HttpResponse(json.dumps({'code': 10000, 'msg': '操作成功'}))

    @classmethod
    def delete(cls, request):
        id = json_request(request, 'id', int)
        exist = tapd_models.tapd_project_conf.objects.filter(id=id, status=1).exists()
        if not exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '不存在或已删除'
            }))
        with transaction.atomic():
            tapd_models.tapd_project_conf.objects.filter(id=id, status=1).update(status=2)
            return HttpResponse(json.dumps({
                'code': 10000,
                'msg': '操作成功'
            }))

    @classmethod
    @request_verify('post', None,
                    {'webhook_url': str, 'users': list})
    def excupt(cls, request):
        tapd_project_id = json_request(request, 'tapd_project_id')
        webhook_url = json_request(request, 'webhook_url', not_null=False)
        users = json_request(request, 'users', list)
        if not webhook_url and not users:
            return HttpResponse(json.dumps({'code': 10005, 'msg': '推送人和webhook地址必须填写一其中个'}))
        try:
            if webhook_url:
                template = TapdTemplate.excupt_try_chat()
                result = DingDingSend.ding_real_chat(template, webhook_url)
                if result['code'] != 1000:
                    return HttpResponse(json.dumps({'code': 10005, 'msg': result['error']}))
            if users:
                userdata = []
                for user in users:
                    ding_userid = tapd_models.mail_list.objects.get(id=user).ding_userid
                    userdata.append(ding_userid)
                template = TapdTemplate.excupt_try_man(userdata)
                result = DingDingSend.ding_real_man(template)
                if result['code'] != 1000:
                    return HttpResponse(json.dumps({'code': 10005, 'msg': result['error']}))

        except Exception as e:
            logger.error('发送消息失败:{}'.format(str(e)))
            return HttpResponse(json.dumps({'code': 10005, 'msg': '发送消息失败'}))
        return HttpResponse(json.dumps({'code': 10000, 'msg': '消息已成功发送'}))

    @classmethod
    @request_verify('post', {'tapd_project_id': int}, {'tapd_project_id': int})
    def tapd_project_demandStatus(cls, request):
        tapd_project_id = json_request(request, 'tapd_project_id', int)
        exist = models.system_config.objects.filter(name='demand_status_{}'.format(tapd_project_id)).exists()
        if not exist:
            return HttpResponse(json.dumps({'code': 10005, 'msg': '该项目不存在'}))
        query = eval(models.system_config.objects.get(name='demand_status_{}'.format(tapd_project_id)).ext)
        query['newDemand'] = '新增需求'
        return HttpResponse(json.dumps({'code': 10000, 'data': query}))

def demand_middle_push():
    pass

