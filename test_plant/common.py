import logging,time
from test_plant import task
from test_management import task as manegeTask
from nextop_tapd import task as tapdTask
from test_tools import task as toolsTask
from test_tools import jenkins_task
from test_plant.task import scheduler,test_plant
from test_yunxiao import task as yunxiaoTask
from test_case.api import swagger_spider,yapi_spider
from test_plant.models import TestPlantTask
import datetime
from test_case.models import CaseTestReport
from test_tools.models import JenKinsAssembly_line

logger = logging.getLogger(__name__)


def method(method_name):
    '''

    :param method_name: 方法名
    :param cache:
    :return:
    '''
    if hasattr(task, method_name):
        return getattr(task,method_name)
    elif hasattr(manegeTask,method_name):
        return getattr(manegeTask, method_name)
    elif hasattr(tapdTask,method_name):
        return getattr(tapdTask, method_name)
    elif hasattr(toolsTask,method_name):
        return getattr(toolsTask, method_name)
    elif hasattr(yunxiaoTask,method_name):
        return getattr(yunxiaoTask, method_name)
    elif hasattr(swagger_spider, method_name):
        return getattr(swagger_spider, method_name)
    elif hasattr(yapi_spider,method_name):
        return getattr(yapi_spider, method_name)
    elif hasattr(jenkins_task,method_name):
        return getattr(jenkins_task, method_name)
    else:
        raise ModuleNotFoundError('没有注册该方法：' + method_name)

def add_job(func_name, task_id, task_type, times, args,start_time=None,end_time=None):
    '''
    增加job
    :param func_name:
    :param task_id:
    :param task_type:
    :param times:
    :param args:
    :return: scheduler实例对象
    '''
    if hasattr(func_name, "__call__"):
        func_name = func_name
    else:
        func_name = method(func_name)

    if task_type == 'cron':
        result = scheduler.add_job(func_name, task_type, year=times['year'], month=times['month'],
                                   day_of_week=times['day_of_week'], hour=times['hour'], minute=times['minute'],
                                   second=times['second'], id=task_id, replace_existing=True, args=args,start_date=start_time,end_date=end_time)
    elif task_type == 'interval':
        result = scheduler.add_job(func_name, task_type, weeks=times['weeks'],
                                   days=times['days'], hours=times['hours'], minutes=times['minutes'],
                                   seconds=times['seconds'], id=task_id, replace_existing=True, args=args,start_date=start_time,end_date=end_time)
    else:
        result = scheduler.add_job(func_name, task_type,
                                   run_date=times,
                                   id=task_id, replace_existing=True, args=args)
    return result


def modify_job(func_name, task_id, task_type, times, args,start_time=None,end_time=None):
    '''
    修改job
    :param func_name:
    :param task_id:
    :param task_type:
    :param times:
    :param args:
    :return: scheduler实例对象
    '''
    if hasattr(func_name, "__call__"):
        func_name = func_name
    else:
        func_name = method(func_name)
    if task_type == 'cron':
        temp_trigger = scheduler._create_trigger(trigger='cron', trigger_args=times)
        result = scheduler.reschedule_job(job_id=task_id, func=func_name, trigger=temp_trigger, args=args,start_date=start_time,end_date=end_time)
        scheduler.modify_job(job_id=task_id,args=args)
    elif task_type == 'interval':
        temp_trigger = scheduler._create_trigger(trigger='interval', trigger_args=times)
        result = scheduler.reschedule_job(job_id=task_id, func=func_name, trigger=temp_trigger, args=args,start_date=start_time,end_date=end_time)
        scheduler.modify_job(job_id=task_id, args=args)
    else:
        temp_trigger = scheduler._create_trigger(trigger='date', trigger_args={
            'run_date': times
        })
        result = scheduler.reschedule_job(job_id=task_id, func=func_name, trigger=temp_trigger,
                                      next_run_time=times,
                                      args=args)
        scheduler.modify_job(job_id=task_id, args=args)
    return result

def ExecutionForPipeline(service_name):
    logger.info('service_name:{}'.format(service_name))
    pipline_id = JenKinsAssembly_line.objects.get(Assembly_name=service_name,Assembly_serverName='uat',status=1).id
    plans = list(TestPlantTask.objects.filter(status=1,is_del=1).values())
    for plan in plans:
        plan['service_name'] = eval(plan['service_name'])
    querys = []
    for plan in plans:
        if pipline_id in plan['service_name']:
            querys.append(plan)
    if not querys:
        logger.error('没有匹配的测试计划')
        return False
    times = int(time.time())
    for query in querys:
        task_id = 'ExecutionForPipeline_'+ str(query['id']) + str(times)
        try:
            scheduler.add_job(test_plant, id=task_id, run_date=datetime.datetime.now()+datetime.timedelta(hours=0,minutes=10,seconds=0),
                              args=[query['task_name'], query['id'], task_id, query['creator'], query['case_list'], query['group_list'], query['project_id'], eval(query['env'])[1], query['account_id'],
                                query['creator'],True,service_name])
        except Exception as e:
            logger.error('添加测试计划执行任务失败：{}'.format(str(e)))
