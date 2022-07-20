# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten
import time
import base64
import requests
import easyocr
import os
from test_plant import models
from apscheduler.schedulers.background import BackgroundScheduler  # 后台线程执行模式
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import datetime
from django.db import transaction
from django.utils import timezone
from functools import wraps
from test_management import models as manage_models
from api_case.views.run import run_func
import logging
from test_management.common import get_k8s_list
from api_case.models import MitData

logger = logging.getLogger(__name__)


def registe_job(*args, **kwargs):
    def registe_parme(func):
        task_name = kwargs['task_name'] if kwargs.__contains__('task_name') else func.__name__
        status = kwargs['status'] if kwargs.__contains__('status') else 1
        try:
            models.ScheduledTask.objects.update_or_create(defaults={
                'task_name': task_name,
                'func_name': func.__name__,
                'status': status
            }, func_name=func.__name__)
            logger.info('定时任务注册成功：' + task_name)
        except Exception as e:
            logger.error('定时任务:{}注册失败：'.format(task_name) + str(e))

        @wraps(func)
        def wrapper(*args, **kwargs):

            return func(*args, **kwargs)

        return wrapper

    return registe_parme


# 初始化及定时任务预置
job_defaults = {
    # 'misfire_grace_time':None,
    'coalesce': True,
    'max_instances': 100
}
executors = {
    'default': ThreadPoolExecutor(20)
}


def my_listener(event):
    times = datetime.datetime.fromtimestamp(event.scheduled_run_time.replace().timestamp())
    if hasattr(event, 'exception'):
        if event.exception:
            logger.error('{}任务执行出错了:{}'.format(event.job_id, event.exception))
        else:
            logger.info('{}任务结束！'.format(event.job_id))
        if 'now' in event.job_id:  # 只记录单次执行的任务
            if event.code == 2 ** 12:
                status = 'Executed'
            elif event.code == 2 ** 13:
                status = 'Error!'
            elif event.code == 2 ** 14:
                status = 'missed'
            else:
                status = 'dontknow'
            models.ScheduledExecution.objects.create(**{
                'job_id': event.job_id,
                'status': status,
                'run_time': times,
                'exception': event.exception,
                'duration': None,
                'finished': None,
                'traceback': event.traceback
            })


scheduler = BackgroundScheduler(executors=executors, job_defaults=job_defaults, timezone='Asia/Shanghai')
scheduler.add_jobstore(DjangoJobStore(), "default")
scheduler.add_listener(my_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
scheduler.start()
models.ScheduledTask.objects.filter().update(status=2)


def test_plant(task_name, plant_id, task_id, creator, case_list, group_list, project_id, env, account_id, account,
               cookie, username):
    logger.info('测试任务开始执行:{}'.format(case_list))
    sql_plant_id = models.TestPlantExcu.objects.create(**{
        'plant_id': plant_id,
        'status': 1,
        'task_id': task_id,
        'create_time': timezone.now(),
        'creator': creator,
        'case_list': case_list,
        'group_list': group_list,
        'project_id': project_id,
        'env': env,
        'account_id': account_id,
        'account': account,
        'cookie': cookie,
        'case_num': None,
        'pass_num': None,
        'lose_num': None,
        'duration': None,
        'report_url': None
    }).id
    env_name = manage_models.envList.objects.get(id=env).server_env
    try:
        report_name = '测试任务-{}-{}'.format(task_name, str(int(time.time())))
        # report_name, project_id, case_list, case_group_list, run_env, run_cookie, user_id, run_user_nickname
        result = run_func(report_name, project_id, case_list, group_list, env_name, cookie, account_id, username)
        status = 2 if result['report_status'] == 1 else 1
    except Exception as e:
        result = None
        status = 5
        logger.error('执行测试任务失败，失败原因：{}'.format(str(e)))
    elapsed = float(result['elapsed'][:-1])
    models.TestPlantExcu.objects.update_or_create(defaults={
        'plant_id': plant_id,
        'status': status,
        'task_id': task_id,
        'create_time': timezone.now(),
        'creator': creator,
        'case_list': case_list,
        'group_list': group_list,
        'project_id': project_id,
        'env': env,
        'account_id': account_id,
        'account': account,
        'cookie': cookie,
        'case_num': result['case_num'] if result else None,
        'pass_num': result['pass_num'] if result else None,
        'lose_num': result['lose_num'] if result else None,
        'duration': elapsed,
        'report_url': '暂未开发'
    }, id=sql_plant_id)
    logger.info('测试任务执行结束')
    return True


@registe_job(task_name='获取k8s环境标签列表')
def update_pro():
    with transaction.atomic():
        save_id = transaction.savepoint()
        try:
            manage_models.envList.objects.filter().update(status=2)
            querys = get_k8s_list()
            datas = []
            datas.append({
                'lable_name': 'nextop-prod',
                'server_env': 'nextop-prod',
                'env_name': 'nextop-prod',
            })
            for query in querys['items']:
                try:
                    data = {}
                    if query['metadata'].__contains__('labels') and query['metadata']['labels'].__contains__('env'):
                        data['lable_name'] = query['metadata']['name']
                        data['server_env'] = query['metadata']['labels']['env']
                        if data['lable_name'] == 'nextop-pre':
                            data['env_name'] = 'nextop-pre'
                        else:
                            data['env_name'] = 'daily'
                        datas.append(data)
                except Exception as e:
                    logger.error('获取联调标签出错，错误原因{}'.format(str(e)))
                    continue
            for data in datas:
                manage_models.envList.objects.update_or_create(defaults={
                    'lable_name': data['lable_name'],
                    'env_name': data['env_name'],
                    'server_env': data['server_env'],
                    'status': 1
                }, lable_name=data['lable_name'])
        except Exception as e:
            logger.error(str(e))
            transaction.savepoint_rollback(save_id)

#
# @registe_job(task_name='定时更新mit抓包接口所属账号信息')
# def updateMitMan():
#     r = requests.session()
#     with transaction.atomic():
#         save_id = transaction.savepoint()
#         try:
#             cookies = MitData.objects.filter(source='抓包').order_by('created_time').values()
#             if cookies:
#                 sucessCookie = []
#                 for cookie in cookies:
#                     if cookie['cookie'] == None or cookie['cookie'] == '':
#                         logger.error('该数据没有cookie')
#                         MitData.objects.filter(id=cookie['id']).updata(source='匹配失败')
#                         continue
#                     for suess in sucessCookie:
#                         for key in suess.keys():
#                             if cookie['cookie'] == key:
#                                 userPhone = suess[key]
#                                 MitData.objects.filter(id=cookie['id']).update(source='匹配成功', cookie=userPhone)
#                                 logger.info('已有相同cookie，直接匹配：{}'.format(userPhone))
#                                 continue
#                     if 'SESSION' not in cookie['cookie']:
#                         session = 'SESSION=' + cookie['cookie']
#                     else:
#                         session = cookie['cookie']
#                     r.headers = {
#                         'x-ca-reqid': return_times(),
#                         'x-ca-reqtime': return_time(),
#                         'origin': 'https://saas.nextop.com',
#                         'referer': 'https://saas.nextop.com/',
#                         'cookie': session
#                     }
#                     url = 'https://' + cookie['host_name']
#                     userinfo = r.get(url + '/user/user/userInfo').json()
#                     if userinfo['code'] != '000000':
#                         logger.error('获取租户列表失败：{}'.format(cookie['id']))
#                         MitData.objects.filter(id=cookie['id']).update(source='匹配失败')
#                         continue
#                     userPhone = userinfo['data']['userInfo']['account']
#                     MitData.objects.filter(id=cookie['id']).update(source='匹配成功', cookie=userPhone)
#                     sucessCookie.append({cookie['cookie']: userPhone})
#         except Exception as e:
#             logger.error(str(e))
#             transaction.savepoint_rollback(save_id)


@registe_job(task_name='更新erp账号信息')
def update_erpAccount():
    account_list = tuple(manage_models.ErpAccount.objects.filter(status=1, is_del=1).values())
    r = requests.session()
    for accountquery in account_list:
        env = accountquery['env']
        account = accountquery['account']
        password = accountquery['password']
        r.headers = {
            'canary': env,
            'x-ca-reqid': return_times(),
            'x-ca-reqtime': return_time(),
            'origin': 'https://saas.nextop.com',
            'referer': 'https://saas.nextop.com/'
        }
        captchaImg = \
            r.get('https://api.nextop.com/auth/login/img?{}'.format(return_time())).json()['data'].split('base64,')[1]
        error_num = 0
        for i in range(3):
            try:
                with open('cap.png', 'wb') as f:
                    f.write(base64.b64decode(captchaImg))
                    f.close()
                    reader = easyocr.Reader(['ch_sim', 'en'])
                    result = reader.readtext('cap.png')
                    captcha = result[0][1]
                    os.remove('cap.png')
                break
            except Exception as e:
                logger.error('图片识别失败：{},原因：{}'.format(account, str(e)))
                error_num += 1
        if error_num >= 3:
            continue

        r.headers = {
            'canary': env,
            'x-ca-reqid': return_times(),
            'x-ca-reqtime': return_time(),
            'origin': 'https://saas.nextop.com',
            'referer': 'https://saas.nextop.com/',

        }
        logger.info('请求头：{},验证码:{}'.format(r.headers, captcha))
        erp_cookie = r.post('https://api.nextop.com/auth/login', json={
            'account': account,
            'password': password,
            'captcha': captcha,
            'rememberMe': True,
            'terminalType': "PC"
        })
        session = r.cookies.get('SESSION') or None
        satoken = r.cookies.get('satoken') or None
        cookie = 'SESSION={}; satoken={}'.format(session, satoken)
        logger.info('request:{},cookie:{},登录返回内容:{}'.format({
            'account': account,
            'password': password,
            'captcha': captcha
        }, cookie, erp_cookie.text))
        logger.info('cookie:{},登录返回内容:{}'.format(cookie, erp_cookie.text))
        if session and satoken and erp_cookie.json()['code'] == '000000':
            logger.info('获取erp-cookie成功:{}'.format(cookie))
            r.headers = {
                'canary': env,
                'x-ca-reqid': return_times(),
                'x-ca-reqtime': return_time(),
                'origin': 'https://saas.nextop.com',
                'referer': 'https://saas.nextop.com/',
                'cookie': cookie

            }
            tenantList = r.get('https://api.nextop.com/user/user/tenant/dropdown?sysIdentification=1').json()['data']
            try:
                manage_models.ErpAccount.objects.filter(id=accountquery['id']).update(
                    cookie=cookie, tenant=tenantList
                )
            except Exception as e:
                logger.error('更新cookie数据失败：{},失败原因:{}'.format(account, str(e)))
                continue
        else:
            logger.error('未获取到cookie，账号account：{}'.format(account))
            continue
        r.cookies.clear()  # 清除实例的旧cookie


@registe_job(task_name='每周一删除两周前的抓包数据')
def del_mitm_data():
    now = datetime.datetime.now()
    last_last_week = now - datetime.timedelta(days=now.weekday() + 14)
    # is_bug不等于1 ，就是已转bug, 不删除
    MitData.objects.filter(created_time__lte=last_last_week, is_bug=1).delete()  # gte 大于等于
    print(f"{last_last_week} 之前的数据已删除！")


def return_times():
    times = str(int(time.time() * 1000)) + '.0125'
    return times


def return_time():
    times = str(int(time.time() * 1000))
    return times
