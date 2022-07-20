# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten
import json
import logging
import asyncio
import os
from test_management import models
from django.core.paginator import Paginator
from django.http import HttpResponse
from nextop_tapd.task import return_tapdSession,get_tapd_pro
from test_management.common import json_request, jwt_token, DateEncoder, request_verify

os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
logger = logging.getLogger(__name__)

class TapdProjectListSet():

    @classmethod
    def list(self, request):
        page = json_request(request, 'page', int)
        limit = json_request(request, 'limit', int)

        # tapd项目配置信息接口
        data = get_tapd_pro()

        # 异步更新项目信息到配置表
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = [asyncio.ensure_future(update_pro(data))]
        loop.run_until_complete(asyncio.wait(task))
        loop.close()

        p = Paginator(data, limit)
        count = p.count
        logging.info('项目查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count, 'page': page, 'code': 10000, 'data': result
        }))

    @classmethod
    @request_verify('post', {'tapd_project_id': str})
    def init(self, request):
        r = return_tapdSession()[0]
        tapd_project_id = json_request(request, 'tapd_project_id', str, not_null=False)
        try:
            plant_req = r.post('https://www.tapd.cn/{}/userviews/edit_show_fields/'.format(tapd_project_id),
                               data={
                                   'data[fields][id]': 'id',
                                   'data[fields][name]': 'name',
                                   'data[fields][version]': 'version',
                                   'data[fields][type]': 'type',
                                   'data[fields][status]': 'status',
                                   'data[fields][story_count]': 'story_count',
                                   'data[fields][tcase_count]': 'tcase_count',
                                   'data[fields][passed_rate]': 'passed_rate',
                                   'data[fields][executed_rate]': 'executed_rate',
                                   'data[fields][case_coverage]': 'case_coverage',
                                   'data[fields][iteration_id]': 'iteration_id',
                                   'data[fields][owner]': 'owner',
                                   'data[fields][creator]': 'creator',
                                   'data[fields][start_date]': 'start_date',
                                   'data[fields][end_date]': 'end_date',
                                   'data[fields][created]': 'created',
                                   'custom_fields': 'id;name;version;type;status;owner;start_date;end_date;creator;created;iteration_id;story_count;tcase_count;passed_rate;executed_rate;case_coverage;custom_field_1;',
                                   'location': '/sparrow/test_plan/plan_list',
                                   'workspace_id': '%s' % tapd_project_id,
                                   'workspace_code': '%s' % tapd_project_id,
                                   'id': '1000000000000278578'
                               })
            logger.info('{}项目执行初始化:测试计划字段'.format(tapd_project_id))
            demand_req = r.post('https://www.tapd.cn/{}/userviews/edit_show_fields/'.format(tapd_project_id),
                                data={
                                    'data[fields][id]': 'id',
                                    'data[fields][name]': 'name',
                                    'data[fields][status]': 'status',
                                    'data[fields][priority]': 'priority',
                                    'data[fields][iteration_id]': 'iteration_id',
                                    'data[fields][owner]': 'owner',
                                    'data[fields][creator]': 'creator',
                                    'data[fields][begin]': 'begin',
                                    'data[fields][due]': 'due',
                                    'data[fields][created]': 'created',
                                    'custom_fields': 'id;name;priority;iteration_id;status;owner;begin;due;creator;created;category_id;',
                                    'location': '/prong/stories/stories_list',
                                    'workspace_id': '%s' % tapd_project_id,
                                    'workspace_code': '%s' % tapd_project_id,
                                    'id': '1000000000000000016'
                                })
            logger.info('{}项目执行初始化:需求字段'.format(tapd_project_id))
            plant_req = r.post('https://www.tapd.cn/api/basic/userviews/edit_show_fields',
                               json={"workspace_id":tapd_project_id, "id": "1000000000000278553",
                                     "location": "/bugtrace/bugreports/my_view",
                                     "custom_fields": "title;version_report;severity;priority;status;current_owner;reporter;created;id;iteration_id;BugStoryRelation_relative_id;bugtype;fixer;resolved",
                                     "dsc_token": "Y2wwDz8osK5wHPAz"})
            if plant_req.json()['meta']['code'] == '0':
                logger.info('{}项目执行初始化:bug字段'.format(tapd_project_id))
            else:
                return HttpResponse(json.dumps({
                    'code': 10005, 'msg': '初始化失败'
                }))
        except Exception as e:
            logger.error(str(e))
            return HttpResponse(json.dumps({
                'code': 10005, 'msg': '初始化失败'
            }))
        return HttpResponse(json.dumps({
            'code': 10000, 'msg': '初始化成功'
        }))


async def update_pro(data):
    models.system_config.objects.update_or_create(defaults={
        'name': 'Tapd_project',
        'ext': data,
        'remark': 'tapdtapd项目配置',
        'status': '1'
    }, name='Tapd_project')


class ProjectListSet():

    @classmethod
    def createProject(cls, request):
        project_name = json_request(request, 'project_name')
        host = json_request(request, 'host')
        remark = json_request(request, 'remark', default='')
        type = json_request(request, 'type', int)  # 1新增/2编辑
        id = json_request(request, 'id', int)
        if type == 2 and not id:
            return HttpResponse(json.dumps({
                'code': 10005, 'msg': '编辑时请传递项目id'
            }))
        userdetail = jwt_token(request)
        logger.info('1234723627383{}'.format(userdetail))
        exist = models.projectMent.objects.filter(host=host).exists()
        if exist and type == 1:
            return HttpResponse(json.dumps({
                'code': 10005, 'msg': '该项目已存在'
            }))
        if type == 2:
            idexist = models.projectMent.objects.filter(id=id).exists()
            if not idexist:
                return HttpResponse(json.dumps({
                    'code': 10005, 'msg': '该项目不存在'
                }))
        try:
            if type == 2:
                models.projectMent.objects.update_or_create(defaults={
                    'project_name': project_name,
                    'host': host,
                    'remark': remark,
                    'creator': userdetail['username'],
                }, id=id)
            else:
                models.projectMent.objects.create(**{
                    'project_name': project_name,
                    'host': host,
                    'remark': remark,
                    'creator': userdetail['username'],
                })
            return HttpResponse(json.dumps({
                'code': 10000, 'msg': '操作成功'
            }))
        except Exception as e:
            logger.error(str(e))
            return HttpResponse(json.dumps({
                'code': 10005, 'msg': '添加失败，请联系测试人员'
            }))

    @classmethod
    def proList(cls, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=20)
        query = models.projectMent.objects.filter().order_by('-create_time').values()
        p = Paginator(tuple(query), limit)
        count = p.count
        logging.info('项目查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'totalNum': count, 'page': page, 'code': 10000, 'items': result, 'msg': '操作成功'
        }, cls=DateEncoder))
