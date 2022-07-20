# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten

import json
import requests
from dateutil.rrule import *
from django.conf import settings
from datetime import datetime
import matplotlib.image as mping  # mping用于读取图片
from pylab import *
import matplotlib.pyplot as plt
from django.db import connection
from django.http import HttpResponse
from test_management.common import json_request, request_verify
from django.core.paginator import Paginator
from test_management.common import DateEncoder, jwt_token
from nextop_tapd import models as tapd_models
import datetime
import logging
from django.db.models import Q
from test_plant.task import scheduler
from nextop_tapd.task import tapd_iteration,tapd_testPlant,tapd_get_TestCase,update_bug_statistic
from test_plant.models import ScheduledExecution
from django.utils import timezone
from django.db import transaction

r = requests.session()
logger = logging.getLogger(__name__)

class tapd_project_bugStatistics():

    @classmethod
    @request_verify('post',check_params={'page':int,'limit':int})
    def groupList(cls,request):
        page = json_request(request,'page',int,not_null=False,default=1)
        limit = json_request(request, 'limit', int, not_null=False, default=20)
        iteration_name = json_request(request, 'iteration_name', str, not_null=False, default=None)
        iteration_id = json_request(request, 'iteration_id', int, not_null=False, default=None)
        test_man = json_request(request, 'test_man', str, not_null=False, default=None)
        query = Q(status=1)
        if iteration_name:
            query &= Q(iteration_name__icontains=iteration_name)
        if test_man:
            query &= Q(owner__icontains=test_man)
        if iteration_id:
            query &= Q(iteration_id=iteration_id)
        plant_querys = tapd_models.tapd_bugStatics.objects.filter(query).values().order_by('-module')
        datas = []
        for query in plant_querys:
            query['riskData'] = eval(query['riskData']) if query['riskData'] else None
            query['convergence_risk_data'] = eval(query['convergence_risk_data']) if query['convergence_risk_data'] else None
            datas.append(query)
        p = Paginator(datas, limit)
        count = p.count
        logging.info('查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count, 'page': page, 'code': 10000, 'data': result
        }, cls=DateEncoder))

    @classmethod
    @request_verify('post',{'plant_id':str})
    def detail(cls,request):
        plant_id = json_request(request,'plant_id',not_null=False,default=None)
        data = {}
        data['demand_data'] = list(tapd_models.tapd_demand_status.objects.filter(
            is_del='1', plant_id=plant_id).values())
        demand_id_list = [x['demand_all_id'] for x in list(tapd_models.tapd_demand_status.objects.filter(
            is_del='1', plant_id=plant_id).values('demand_all_id'))]
        if demand_id_list == []:
            logger.info('该迭代未维护任何需求')
        data['bug_data'] = list(
            tapd_models.tapd_bug_status.objects.filter(is_del='1', demand_id__in=demand_id_list).values().order_by(
                '-create_Time'))
        data['bug_no_data'] = list(tapd_models.tapd_bug_status.objects.filter(is_del='1', demand_id__in=demand_id_list).exclude(
            status__in=['已关闭', '已验证', '已解决', '已拒绝']).values().order_by('-create_Time'))
        data['bug_all_level_data'] = list(
            tapd_models.tapd_bug_status.objects.filter(is_del='1', demand_id__in=demand_id_list,
                                                       bug_level__in=['fatal', 'serious']).values().order_by(
                '-create_Time'))

        # 重复打开的bug
        bug_reruns = tapd_models.tapd_push_record.objects.filter(type='bug', new_status='重新打开').values()
        bugs = []
        bugs_detail = {}
        for bug_rerun in bug_reruns:
            bug_id = eval(bug_rerun['push_content'])['bug_id']
            exist = tapd_models.tapd_bug_status.objects.filter(bug_id=bug_id, demand_id__in=demand_id_list,
                                                               is_del='1').exists()
            if exist and bug_id not in bugs:
                bugs.append(bug_id)
                bugs_detail[bug_id] = 1
            elif exist and bug_id in bugs:
                bugs_detail[bug_id] += 1
        data['bug_rerun_detail'] = bugs_detail
        # 重复打开bug列表
        data['bug_rerun_data'] = list(
            tapd_models.tapd_bug_status.objects.filter(bug_id__in=bugs).values().order_by('-create_Time'))

        # 延期解决bug数
        yanqi_bug = []
        yanqi_bug_times = []
        all_bug_querys = tapd_models.tapd_bug_status.objects.filter(is_del='1', demand_id__in=demand_id_list).values()
        for all_bug_query in all_bug_querys:
            if all_bug_query['create_Time'] == '--' or all_bug_query['ok_Time'] == '--':
                continue
            bug_create_time = int(time.mktime(time.strptime(all_bug_query['create_Time'], '%Y-%m-%d %H:%M:%S')))
            bug_ok_time = int(time.mktime(time.strptime(all_bug_query['ok_Time'], '%Y-%m-%d %H:%M:%S')))
            bug_middle = all_bug_query['bug_level']
            bug_time = bug_ok_time - bug_create_time
            if bug_middle in ['fatal', 'serious'] and bug_time > 60 * 60 * 4:
                yanqi_bug.append(all_bug_query['bug_id'])
                yanqi_bug_times.append({'bug_id': all_bug_query['bug_id'], 'yanqi_times': bug_time / 60 / 60})
            elif bug_middle not in ['fatal', 'serious'] and bug_time > 60 * 60 * 24:
                yanqi_bug.append(all_bug_query['bug_id'])
                yanqi_bug_times.append({'bug_id': all_bug_query['bug_id'], 'yanqi_times': bug_time / 60 / 60})
        data['yanqi_bug_data'] = list(
            tapd_models.tapd_bug_status.objects.filter(bug_id__in=yanqi_bug).values().order_by('-create_Time'))
        data['yanqi_bug_times'] = yanqi_bug_times
        data['before_block_data'] = list(tapd_models.tapd_TestCase.objects.filter(plant_big_id=plant_id,
                                                                                  zhusai_status='1').values())  # 阻塞用例详情
        return HttpResponse(json.dumps({
            'code':10000,
            'msg':'查询成功',
            'data':data
        },cls=DateEncoder))




    @classmethod
    @request_verify('post')
    def update_now(cls,request):
        exist = ScheduledExecution.objects.filter(job_id__in=['testRiskUpdateIteration_now','testRiskUpdatePlant_now','testRiskUpdateTestCase_now','testUpdateBugStatistic_now']).exists()
        if exist:
            query = ScheduledExecution.objects.filter(job_id__in=['testRiskUpdateIteration_now','testRiskUpdatePlant_now','testRiskUpdateTestCase_now','testUpdateBugStatistic_now']).values().order_by('-run_time')[0]
            diff = timezone.now() - query['run_time']
            if diff.seconds < 60:
                return HttpResponse(json.dumps({'code': 10005, 'msg': '1分钟内只允许同步一次'}))
        with transaction.atomic():
            try:
                save_id = transaction.savepoint()
                scheduler.add_job(tapd_iteration, run_date=datetime.datetime.now(),id='testRiskUpdateIteration_now')
                scheduler.add_job(tapd_testPlant, run_date=datetime.datetime.now(),id='testRiskUpdatePlant_now')
                scheduler.add_job(tapd_get_TestCase, run_date=datetime.datetime.now(), id='testRiskUpdateTestCase_now')
                scheduler.add_job(update_bug_statistic, run_date=datetime.datetime.now(), id='testUpdateBugStatistic_now')
                ScheduledExecution.objects.create(**{
                    'job_id': 'testRiskUpdateIteration_now',
                    'status': 'Executed',
                    'run_time': timezone.now(),
                    'exception': None,
                    'duration': None,
                    'finished': None,
                    'traceback': None
                })
            except Exception as e:
                transaction.savepoint_rollback(save_id)
                return HttpResponse(json.dumps({'code': 10005, 'msg': '操作失败：{}'.format(str(e))}))
            transaction.savepoint_commit(save_id)
        return HttpResponse(json.dumps({'code': 10000, 'msg': '操作成功'}))