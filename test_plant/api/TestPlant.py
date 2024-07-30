import json
import logging
import time

from test_plant import models
from django.http import HttpResponse
from django.core.paginator import Paginator
from test_plant.task import scheduler, test_plant
from test_plant.common import add_job, modify_job,method
import datetime
from test_management.common import json_request, DateEncoder,jwt_token,request_verify
from django.db import transaction
from django_apscheduler import models as apscheduler_model
from django.db.models import Q
from test_management import models as manageModels
from django.utils import timezone
from test_case.models import Case,CaseGroup,CaseTestReport
from test_case.views import RunGroupCase
from django_apscheduler.jobstores import JobLookupError

logger = logging.getLogger(__name__)


class TestPlantView():

    @classmethod
    def create(cls, request):
        status = json_request(request, 'status', int)
        task_name = json_request(request, 'task_name')
        case_list = json_request(request, 'case_list', list)
        group_list = json_request(request,'group_list',list)
        task_type = json_request(request, 'task_type')
        project_id = json_request(request,'project_id')
        env = json_request(request,'env',list)
        account_id = json_request(request, 'account_id', int)
        datetimes = json_request(request,'datetimes') if task_type == 'date' else None
        start_time = json_request(request, 'start_time', not_null=False) if task_type not in ['now','date'] else None
        end_time = json_request(request, 'end_time', not_null=False) if task_type not in ['now','date']  else None
        times = json_request(request, 'times', dict) if task_type not in ['now','date'] else None
        dingding = json_request(request, 'dingding',default=None)
        service_name = json_request(request, 'service_name', str, default=None)
        creator = jwt_token(request)['username']
        task_id = 'test_plant_' + str(int(time.time())) if task_type not in ['date','now'] else 'test_plant_' + str(int(time.time())) + '_now'
        if status == 2 and task_type == 'now':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '不允许禁用时立即执行'
            }))
        if task_type == 'now':
            datetimes = datetime.datetime.now()
        exec_time = times if times else datetimes
        with transaction.atomic():
            save_id = transaction.savepoint()
            id = models.TestPlantTask.objects.create(**{
                'status': status,
                'task_id': task_id,
                'task_name': task_name,
                'creator': creator,
                'case_list': case_list,
                'group_list': group_list,
                'project_id':project_id,
                'env':env,
                'account_id':account_id,
                'account':'',
                'cookie':'',
                'exec_type': task_type,
                'exec_time': exec_time,
                'dingding': dingding,
                'service_name':service_name
            }).id
            try:
                if task_type == 'date':
                    datetimes = timezone.datetime.strptime(datetimes,"%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)#前端传的UTC时间。。。
                    scheduler.add_job(test_plant, id=task_id, run_date=datetimes, args=[task_name,id,task_id,creator,case_list,group_list,project_id,env[1],account_id,creator])
                elif task_type == 'now':
                    scheduler.add_job(test_plant, id=task_id, run_date=datetime.datetime.now()+datetime.timedelta(hours=0,minutes=0,seconds=3), args=[task_name,id,task_id,creator,case_list,group_list,project_id,env[1],account_id,creator])
                else:
                    add_job(test_plant, task_id, task_type, times, [task_name,id,task_id,creator,case_list,group_list,project_id,env[1],account_id,creator], start_time, end_time)
                if status == 1:
                    scheduler.resume_job(task_id)
                if status == 2:
                    scheduler.pause_job(task_id)
            except Exception as e:
                logger.error('添加测试任务失败:{}'.format(str(e)))
                transaction.savepoint_rollback(save_id)
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '添加测试任务失败:{}'.format(str(e))
                }))
            transaction.savepoint_commit(save_id)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '创建测试任务成功'
        }))

    @classmethod
    def update(cls, request):
        '''
        修改测试任务
        :param request:
        :return:
        '''
        plant_id = json_request(request, 'plant_id', int)  # 定时任务构建的id
        status = json_request(request, 'status', int)  # 启用禁用状态
        task_name = json_request(request, 'task_name')  # 自定义taskname，用于列表显示
        case_list = json_request(request, 'case_list', list)
        group_list = json_request(request,'group_list',list)
        task_type = json_request(request, 'task_type')  # 执行策略：定时/轮训/指定时间
        times = json_request(request, 'times', dict) if task_type not in ['now','date'] else None # 策略执行时间,dict[task_type]
        datetimes = json_request(request,'datetimes') if task_type == 'date' else None
        start_time = json_request(request, 'start_time') if task_type != 'date' else None
        end_time = json_request(request, 'end_time') if task_type != 'date' else None
        dingding = json_request(request, 'dingding',list,not_null=False,default=None)
        project_id = json_request(request, 'project_id')
        env = json_request(request, 'env',list)
        account_id = json_request(request, 'account_id',int)
        plant_exist = models.TestPlantTask.objects.filter(id=plant_id, is_del=1).exists()
        task_old_type = models.TestPlantTask.objects.get(id=plant_id,is_del=1).exec_type
        service_name = json_request(request, 'service_name',str,default=None)
        creator = models.TestPlantTask.objects.get(id=plant_id).creator
        if not plant_exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '计划不存在或已删除'
            }))
        if status == 2 and task_type == 'now':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '不允许禁用时立即执行'
            }))
        if task_old_type == 'now':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '执行一次时不允许修改'
            }))
        if task_old_type == 'date' and task_type != 'date':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '固定执行时不允许修改为其他执行方式'
            }))
        if task_old_type not in ['date','now'] and task_type in ['date','now']:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '多次执行时，只能修改执行方式为cron或interval'
            }))
        task_id = models.TestPlantTask.objects.get(id=plant_id,is_del=1).task_id
        exec_time = times if times else datetimes
        if task_type == 'date':
            oldtime = models.TestPlantTask.objects.get(id=plant_id).exec_time
            oldtime = timezone.datetime.strptime(oldtime, "%Y-%m-%dT%H:%M:%S.%fZ")
            if oldtime < datetime.datetime.now():
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '已经超时的date类型计划无法修改，请重新添加新计划'
                }))
        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                models.TestPlantTask.objects.filter(id=plant_id,is_del=1).update(**{
                    'status': status,
                    'task_id': task_id,
                    'task_name': task_name,
                    'case_list': case_list,
                    'group_list': group_list,
                    'project_id': project_id,
                    'env': env,
                    'account_id': account_id,
                    'exec_type': task_type,
                    'exec_time': exec_time,
                    'dingding': dingding,
                    'service_name':service_name
                })
                try:
                    if status == 1:
                        if task_type == 'date':
                            logger.error('???{}'.format(timezone.datetime.strptime(datetimes,"%Y-%m-%dT%H:%M:%S.%fZ")))
                            datetimes = timezone.datetime.strptime(datetimes,"%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)#前端传的UTC时间。。。
                            modify_job(test_plant, task_id, task_type, datetimes, [task_name,plant_id,task_id,creator,case_list,group_list,project_id,env[1],account_id,creator])
                        else:
                            modify_job(test_plant, task_id, task_type, times, [task_name,plant_id,task_id,creator,case_list,group_list,project_id,env[1],account_id,creator], start_time,
                                       end_time)
                        scheduler.resume_job(task_id)
                    elif status == 2:
                        scheduler.pause_job(task_id)
                    else:
                        return HttpResponse(json.dumps({
                            'code': 10005,
                            'msg': 'status参数不合法'
                        }))
                except JobLookupError as e:
                    logger.error('修改计划失败，计划任务不存在，尝试重新添加任务')
                    add_job(test_plant, task_id, task_type, times,
                               [task_name, plant_id, task_id, creator, case_list, group_list, project_id, env[1],
                                account_id, creator], start_time,
                               end_time)
                    return HttpResponse(json.dumps({
                        'code': 10000,
                        'msg': '重新添加测试任务成功'
                    }))
                except Exception as e:
                    logger.error('修改测试任务失败{}'.format(str(e)))
                    transaction.savepoint_rollback(save_id)
                    return HttpResponse(json.dumps({
                        'code': 10005,
                        'msg': '修改测试任务失败{}'.format(str(e))
                    }))
            except Exception as e:
                logger.error(str(e))
                transaction.savepoint_rollback(save_id)
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '数据库错误:{}'.format(str(e))
                }))
            transaction.savepoint_commit(save_id)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '修改测试任务成功'
        }))

    @classmethod
    def plant_list(cls, request):
        page = json_request(request, 'page', int)
        limit = json_request(request, 'limit', int)
        query = Q(is_del=1)
        planName = json_request(request,'planName',default=None)
        status = json_request(request,'status',int,default=None)
        creator = json_request(request,'creator',not_null=False)
        createTime = json_request(request,'createTime',list,default=None)
        if planName:
            query &= Q(task_name__icontains=planName)
        if status:
            query &= Q(status=status)
        if creator:
            query &= Q(creator__icontains=creator)
        if createTime:
            start = timezone.datetime.strptime(createTime[0], "%Y-%m-%dT%H:%M:%S.%fZ")
            end = timezone.datetime.strptime(createTime[1], "%Y-%m-%dT%H:%M:%S.%fZ")
            query &= Q(create_time__range=[start,end])
        querys = models.TestPlantTask.objects.filter(query).order_by('-create_time').values() or []
        datas = []
        for query in querys:
            if 'now' not in query['task_id']:
                query['execution_status'] = \
                apscheduler_model.DjangoJobExecution.objects.filter(job_id=query['task_id']).values()[0][
                    'status'] if apscheduler_model.DjangoJobExecution.objects.filter(
                    job_id=query['task_id']).exists() else None#Error!：错误 、Executed：正常、Started execution：执行中
                query['execution_run_time'] = \
                    apscheduler_model.DjangoJobExecution.objects.filter(job_id=query['task_id']).values()[0][
                        'run_time'] if apscheduler_model.DjangoJobExecution.objects.filter(
                        job_id=query['task_id']).exists() else None
            else:
                query['execution_status'] = \
                models.ScheduledExecution.objects.filter(job_id=query['task_id']).values()[0][
                    'status'] if models.ScheduledExecution.objects.filter(job_id=query['task_id']).exists() else None
                query['execution_run_time'] = \
                    models.ScheduledExecution.objects.filter(job_id=query['task_id']).values()[0][
                        'run_time'] if models.ScheduledExecution.objects.filter(
                        job_id=query['task_id']).exists() else None
            if query['exec_type'] in ['date','now']:
                pass
            else:
                query['exec_time'] = eval(query['exec_time'])
            datas.append(query)
        p = Paginator(datas, limit)  # 实例化分页对象
        count = p.count
        logging.info('测试任务查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'data': result
        }, cls=DateEncoder, ensure_ascii=False))

    @classmethod
    def plant_executions_list(cls, request):
        '''
        计划执行记录
        :param request:
            plant_id:测试计划的id
        :return:
            'count': 执行记录总条数,
            'code': 10000,
            'page': 当前页码,
            'data': {
                    status：执行/失败，1成功；2失败，3正在执行
                    runtime：执行时间
                    duration：执行花费时长：秒
                    exception：执行失败时有值：错误原因
                    type：触发方式：自动执行/手动触发
                    }
        '''
        plant_id = json_request(request, 'plant_id', int)
        page = json_request(request, 'page', int)
        limit = json_request(request, 'limit', int)
        if not models.TestPlantTask.objects.filter(id=plant_id,is_del=1).exists():
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '计划不存在或已被删除'
            }))
        task_id = models.TestPlantTask.objects.get(id=plant_id,is_del=1).task_id
        # querys = models.TestPlantExcu.objects.filter(task_id=task_id).values().order_by('-create_time') or []
        nex_query = []
        querys = CaseTestReport.objects.filter(report_name__icontains=task_id).values().order_by('-created_time')
        for query in querys:
            env_querys = manageModels.env.objects.filter(id=int(query['run_env'])).values()
            if env_querys:
                env_name = env_querys[0]['env_name']
            else:
                env_name = '未知'
            query['env'] = env_name
            nex_query.append(query)
        p = Paginator(tuple(querys), limit)  # 实例化分页对象
        count = p.count
        logging.info('执行记录查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'data': result
        }, cls=DateEncoder, ensure_ascii=False))

    @classmethod
    def delete(cls, request):
        plant_id = json_request(request, 'plant_id', int)
        exsit = models.TestPlantTask.objects.filter(id=plant_id,is_del=1).exists()
        query = models.TestPlantTask.objects.get(id=plant_id,is_del=1)
        jobexsit = apscheduler_model.DjangoJob.objects.filter(id=query.task_id).exists()
        if not exsit:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '计划不存在或已被删除'
            }))
        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                query.is_del = 2
                query.save()
                if jobexsit:
                    scheduler.pause_job(query.task_id)
            except Exception as e:
                logger.error('删除计划失败:{}'.format(str(e)))
                transaction.savepoint_rollback(save_id)
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '删除计划失败:{}'.format(str(e))
                }))
            transaction.savepoint_commit(save_id)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '计划删除成功'
        }))

    @classmethod
    @request_verify('post',{},{'caseList':list,'caseGroupList':list})
    def PlantCaseList(cls,request):
        caseList = json_request(request,'caseList',list)
        caseGroupList = json_request(request, 'caseGroupList', list)
        case,group = [],[]
        for query in caseList:
            case.append(list(Case.objects.filter(id=query).values())[0])
        for group_query in caseGroupList:
            group.append(list(CaseGroup.objects.filter(id=group_query).values())[0])
        return HttpResponse(json.dumps({
            'code':10000,
            'data':{
                'case':case,
                'cases':group
            },
            'msg':'查询成功'
        },cls=DateEncoder))

    @classmethod
    @request_verify('post',need_params={'report_id':list})
    def checkReportStatus(cls,request):
        report_id = json_request(request,'report_id',list)
        report_exist = CaseTestReport.objects.filter(id__in=report_id).exists()
        if not report_exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '报告不存在或已被删除'
            }))
        querys = CaseTestReport.objects.filter(id__in=report_id)
        datas = []
        for query in querys:
            datas.append({'report_id':query.id,
                          'status':query.report_status,
                          'create_time':query.created_time,
                          'case_num':query.case_num,
                          'pass_num':query.pass_num,
                          'lose_num':query.lose_num})
        return HttpResponse(json.dumps({
                'code': 10000,
                'msg': '操作成功',
                'data':datas
            },cls=DateEncoder))

    @classmethod
    def execution_one(cls, request):
        excu_id = json_request(request, 'excu_id', int)
        creator = jwt_token(request)['username']
        task_exist = models.TestPlantTask.objects.filter(id=excu_id, is_del=1).exists()
        if not task_exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '任务不存在或已被删除'
            }))
        query = models.TestPlantTask.objects.get(id=excu_id, is_del=1)
        task_id = query.task_id if 'now' in query.task_id else query.task_id + '_now'
        scheduler.add_job(test_plant, id=task_id, run_date=datetime.datetime.now()+datetime.timedelta(hours=0,minutes=0,seconds=3),
                          args=[query.task_name, excu_id, task_id, creator, query.case_list, query.group_list, query.project_id, eval(query.env)[1], query.account_id,
                                creator])
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '执行成功'
        }))


