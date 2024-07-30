import json
import logging
import time

from test_plant import models
from django.http import HttpResponse
from django.core.paginator import Paginator
from test_plant.task import scheduler
from test_plant.common import method, add_job, modify_job
import datetime
from django.utils import timezone
from test_management.common import json_request, DateEncoder, jwt_token
from django.db import transaction
from django.db.models import Q
from django_apscheduler import models as apscheduler_model

logger = logging.getLogger(__name__)


class ScheduledTaskListSet():

    @classmethod
    def list(cls, request):
        page = json_request(request, 'page', int,default=1)
        limit = 100
        querys = models.ScheduledTask.objects.filter(status=1).values() or []
        p = Paginator(tuple(querys), limit)  # 实例化分页对象
        count = p.count
        logging.info('定时任务查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'data': result
        }))

    @classmethod
    def job_list(self, request):
        page = json_request(request, 'page', int)
        limit = json_request(request, 'limit', int)
        query = Q(is_del=1)
        taskName = json_request(request, 'taskName', default=None)
        status = json_request(request, 'status', int, default=None)
        creator = json_request(request, 'creator',not_null=False)
        createTime = json_request(request, 'createTime', list, default=None)

        if taskName:
            query &= Q(task_name__icontains=taskName)
        if status:
            query &= Q(status=status)
        if creator:
            query &= Q(creator__icontains=creator)
        if createTime:
            start = timezone.datetime.strptime(createTime[0], "%Y-%m-%dT%H:%M:%S.%fZ")
            end = timezone.datetime.strptime(createTime[1], "%Y-%m-%dT%H:%M:%S.%fZ")
            query &= Q(create_time__range=[start, end])
        querys = models.ScheduledTaskExcu.objects.filter(query).order_by('-create_time').values() or []
        datas = []
        for query in querys:
            query['next_run_time'] = scheduler.get_job(job_id=query['task_id']).next_run_time if scheduler.get_job(
                job_id=query['task_id']) else None
            if 'now' not in query['task_id']:
                query['execution_status'] = \
                    apscheduler_model.DjangoJobExecution.objects.filter(job_id=query['task_id']).values()[0][
                        'status'] if apscheduler_model.DjangoJobExecution.objects.filter(
                        job_id=query['task_id']).exists() else None  # Error!：错误 、Executed：正常、Started execution：执行中
                query['execution_run_time'] = \
                    apscheduler_model.DjangoJobExecution.objects.filter(job_id=query['task_id']).values()[0][
                        'run_time'] if apscheduler_model.DjangoJobExecution.objects.filter(
                        job_id=query['task_id']).exists() else None
            else:
                query['execution_status'] = \
                    models.ScheduledExecution.objects.filter(job_id=query['task_id']).values()[0][
                        'status'] if models.ScheduledExecution.objects.filter(
                        job_id=query['task_id']).exists() else None
                query['execution_run_time'] = \
                    models.ScheduledExecution.objects.filter(job_id=query['task_id']).values()[0][
                        'run_time'] if models.ScheduledExecution.objects.filter(
                        job_id=query['task_id']).exists() else None
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
        }, cls=DateEncoder, ensure_ascii=False))

    @classmethod
    def job_executions_list(cls, request):
        '''
        执行记录
        :param request:
        :return:
        '''
        excu_id = json_request(request, 'excu_id', int)
        page = json_request(request, 'page', int)
        limit = json_request(request, 'limit', int)
        task_id = models.ScheduledTaskExcu.objects.get(id=excu_id).task_id
        querys = apscheduler_model.DjangoJobExecution.objects.filter(job_id=task_id).values() or []
        date_querys = models.ScheduledExecution.objects.filter(job_id=task_id).values() or []
        handle_query = models.ScheduledExecution.objects.filter(job_id=task_id + '_now').values() or []
        datas = []
        for query in querys:
            data = {}
            data['status'] = query['status']
            data['runtime'] = query['run_time']
            data['duration'] = query['duration'] if query['duration'] else '等待执行完成'
            data['exception'] = query['exception']
            data['type'] = 1
            datas.append(data)
        for handle in handle_query:
            data = {}
            data['status'] = handle['status']
            data['runtime'] = handle['run_time']
            data['duration'] = handle['duration']
            data['exception'] = handle['exception']
            data['type'] = 2
            datas.append(data)
        for date in date_querys:
            data = {}
            data['status'] = date['status']
            data['runtime'] = date['run_time']
            data['duration'] = date['duration']
            data['exception'] = date['exception']
            data['type'] = 1
            datas.append(data)
        datas.sort(key=lambda elem: elem['runtime'], reverse=True)
        p = Paginator(datas, limit)  # 实例化分页对象
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
    def create(cls, request):
        '''
        创建定时任务
        :param request:
        :return:
        '''
        regjob_id = json_request(request, 'regjob_id', int)  # 定时任务的id
        status = json_request(request, 'status', int)  # 启用禁用状态
        task_name = json_request(request, 'task_name')  # 自定义taskname，用于列表显示
        task_type = json_request(request, 'task_type')  # 执行策略：定时/轮训/指定时间
        start_time = json_request(request, 'start_time', not_null=False) if task_type != 'date' else None
        end_time = json_request(request, 'end_time', not_null=False) if task_type != 'date' else None
        times = json_request(request, 'times', dict) if task_type != 'date' else None  # 策略执行时间,dict[task_type]
        datetimes = json_request(request, 'datetimes')
        args = json_request(request, 'args', list)  # 执行方法参数，需传递数组格式[1,2,3]对应参数
        remark = json_request(request, 'remark')
        creator = jwt_token(request)['username']
        task_exist = models.ScheduledTask.objects.filter(id=regjob_id, status=1).exists()
        if not task_exist:
            return HttpResponse(json.dumps({
                'code': 10002,
                'msg': '任务方法不存在或已删除'
            }))
        # 如果为只执行一次，则进行标记
        task_id = 'Scheduled_task_' + str(int(time.time())) if task_type != 'date' else 'Scheduled_task_' + str(
            int(time.time())) + '_now'
        func_name = models.ScheduledTask.objects.get(id=regjob_id).func_name
        exec_time = times if times else datetimes
        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                models.ScheduledTaskExcu.objects.create(**{
                    'status': status,
                    'task_name': task_name,
                    'func_name': func_name,
                    'regjob_id': regjob_id,
                    'task_id': task_id,
                    'task_type': task_type,
                    'times': exec_time,
                    'start_time': start_time,
                    'end_time': end_time,
                    'args': args,
                    'creator': creator,
                    'create_time': timezone.now(),
                    'remark': remark
                })
                try:
                    if task_type != 'date':
                        add_job(func_name, task_id, task_type, times, args, start_time, end_time)
                    else:
                        datetimes = timezone.datetime.strptime(datetimes,"%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)#前端传的UTC时间。。。
                        add_job(func_name, task_id, task_type, datetimes, args)
                    if status == 1:
                        scheduler.resume_job(task_id)
                    if status == 2:
                        scheduler.pause_job(task_id)
                except Exception as e:
                    logger.error('添加定时任务失败:{}'.format(str(e)))
                    transaction.savepoint_rollback(save_id)
                    return HttpResponse(json.dumps({
                        'code': 10005,
                        'msg': '添加定时任务失败:{}'.format(str(e))
                    }))

            except Exception as e:
                logger.error('数据库错误:{}'.format(str(e)))
                transaction.savepoint_rollback(save_id)
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '数据库错误:{}'.format(str(e))
                }))
            transaction.savepoint_commit(save_id)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '创建定时任务成功'
        }))

    @classmethod
    def update(cls, request):
        '''
        修改定时任务
        :param request:
        :return:
        '''
        regjob_id = json_request(request, 'regjob_id', int)  # 定时任务的id
        excu_id = json_request(request, 'excu_id', int)  # 定时任务构建的id
        status = json_request(request, 'status', int)  # 启用禁用状态
        task_name = json_request(request, 'task_name')  # 自定义taskname，用于列表显示
        task_type = json_request(request, 'task_type')  # 执行策略：定时/轮训/指定时间
        times = json_request(request, 'times', dict) if task_type != 'date' else None  # 策略执行时间,dict[task_type]
        datetimes = json_request(request, 'datetimes') if task_type == 'date' else None
        args = json_request(request, 'args', list)  # 执行方法参数，需传递数组格式[1,2,3]对应参数
        remark = json_request(request, 'remark')
        start_time = json_request(request, 'start_time') if task_type != 'date' else None
        end_time = json_request(request, 'end_time') if task_type != 'date' else None
        creator = jwt_token(request)['username']
        task_exist = models.ScheduledTask.objects.filter(id=regjob_id, status=1).exists()

        if not task_exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '任务方法不存在或已删除'
            }))
        func_name = models.ScheduledTask.objects.get(id=regjob_id).func_name
        excu_exist = models.ScheduledTaskExcu.objects.filter(id=excu_id).exists()
        if not excu_exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '任务不存在或已删除'
            }))
        task_id = models.ScheduledTaskExcu.objects.get(id=excu_id).task_id
        task_old_type = models.ScheduledTaskExcu.objects.get(id=excu_id).task_type
        if task_old_type == 'date' and task_type != 'date':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '固定时间执行的任务不能修改执行方式'
            }))
        if task_old_type != 'date' and task_type == 'date':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '多次构建的任务不允许修改为固定执行，因为会导致执行记录全部丢失'
            }))
        exec_time = times if times else datetimes
        if task_type == 'date':
            oldtime = models.ScheduledTaskExcu.objects.get(id=excu_id).times
            oldtime = timezone.datetime.strptime(oldtime, "%Y-%m-%dT%H:%M:%S.%fZ")
            if oldtime < datetime.datetime.now():
                print(oldtime,datetime.datetime.now())
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '已经超时的date类型任务无法修改，请重新添加新任务'
                }))
        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                models.ScheduledTaskExcu.objects.filter(id=excu_id).update(**{
                    'status': status,
                    'task_name': task_name,
                    'func_name': func_name,
                    'regjob_id': regjob_id,
                    'task_id': task_id,
                    'task_type': task_type,
                    'times': exec_time,
                    'start_time': start_time,
                    'end_time': end_time,
                    'args': args,
                    'creator': creator,
                    'create_time': timezone.now(),
                    'remark': remark
                })
                try:
                    if status == 1:
                        if task_type != 'date':
                            modify_job(func_name, task_id, task_type, times, args, start_time, end_time)
                        else:
                            datetimes = timezone.datetime.strptime(datetimes,"%Y-%m-%dT%H:%M:%S.%fZ") + datetime.timedelta(hours=8)#前端传的UTC时间。。。
                            modify_job(func_name, task_id, task_type, datetimes, args)
                        scheduler.resume_job(task_id)
                    elif status == 2:
                        scheduler.pause_job(task_id)
                    else:
                        return HttpResponse(json.dumps({
                            'code': 10005,
                            'msg': 'status参数不合法'
                        }))
                except Exception as e:
                    logger.error('修改定时任务失败{}'.format(str(e)))
                    transaction.savepoint_rollback(save_id)
                    return HttpResponse(json.dumps({
                        'code': 10005,
                        'msg': '修改定时任务失败{}'.format(str(e))
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
            'msg': '修改定时任务成功'
        }))

    @classmethod
    def delete(cls, request):
        excu_id = json_request(request, 'excu_id', int)
        query = models.ScheduledTaskExcu.objects.get(id=excu_id)
        jobexsit = apscheduler_model.DjangoJob.objects.filter(id=query.task_id).exists()
        if not query:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '任务不存在或已被删除'
            }))
        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                query.is_del = 2
                query.save()
                if jobexsit:
                    scheduler.pause_job(query.task_id)
            except Exception as e:
                logger.error('删除任务失败:{}'.format(str(e)))
                transaction.savepoint_rollback(save_id)
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '删除任务失败:{}'.format(str(e))
                }))
            transaction.savepoint_commit(save_id)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '任务删除成功'
        }))

    @classmethod
    def execution_one(cls, request):
        excu_id = json_request(request, 'excu_id', int)
        task_exist = models.ScheduledTaskExcu.objects.filter(id=excu_id, is_del=1).exists()
        if not task_exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '任务不存在或已被删除'
            }))
        query = models.ScheduledTaskExcu.objects.get(id=excu_id, is_del=1)
        task_id = query.task_id if 'now' in query.task_id else query.task_id + '_now'
        func_name = query.func_name
        args = query.args
        scheduler.add_job(method(func_name), run_date=datetime.datetime.now()+datetime.timedelta(hours=0,minutes=0,seconds=5), args=eval(args), id=task_id)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '执行成功'
        }))
