import logging
from test_plant import task
from test_management import task as manegeTask
from nextop_tapd import task as tapdTask
from test_tools import task as toolsTask
from test_plant.task import scheduler

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
        print(times)
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
