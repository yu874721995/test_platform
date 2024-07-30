# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten
import time
import pymysql
from pymysql import cursors
import requests
from test_plant import models
from apscheduler.schedulers.background import BackgroundScheduler  # 后台线程执行模式
from django_apscheduler.jobstores import DjangoJobStore, register_events, register_job
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import datetime
from django.db import transaction
from random import randint
from functools import wraps
from test_management import models as manage_models
import logging
from test_management.common import get_k8s_list,updateToken
from api_case.models import MitData,SwaggerApi
from test_management.models import projectMent,env,moduleMent
import django.db as db
from test_case.views import RunGroupCase
from test_case.models import CaseTestReport,Case,CaseGroup
from nextop_tapd.models import mail_list
from pypinyin import lazy_pinyin

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
    'max_instances': 200
}
executors = {
    'default': ThreadPoolExecutor(200)
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


def test_plant(task_name, plant_id, task_id, creator, case_list, group_list, project_id, env, account_id,username,formPipeline=False,service_name=None):
    logger.info('测试任务开始执行:{}'.format(task_name))
    logger.info('执行入参：{},{},{},{},{},{},{},{},{}'.format(task_name,plant_id,task_id,creator,case_list,group_list,project_id,env,account_id))
    plant_name = models.TestPlantTask.objects.get(id=plant_id).task_name
    report_name = '测试计划-' + plant_name
    if formPipeline:
        report_name = 'UAT流水线:{}-自动执行测试计划-'.format(service_name) + plant_name
    #兼容执行一次时实时添加的任务
    if isinstance(group_list,str):
        group_list = eval(group_list)
    # 查询组合用例中所有用例设置的账号
    execution_accounts = [account_id]
    for groupId in group_list:
        case_list = CaseGroup.objects.get(id=groupId).caseId_list
        for case_id in eval(case_list):
            execution_account = Case.objects.get(id=case_id).execution_account
            # 去重账号
            if execution_account not in execution_accounts and execution_account:
                execution_accounts.append(execution_account)
    # update_erpAccount(execution_account) #更新用例执行账号
    updateToken(execution_accounts)  # 更新用例执行账号token
    try:
        #创建测试报告记录
        runTaskId = creator + '_' + task_id + '_' + str(int(time.time())) + str(randint(10000000,99999999))#确保job_id唯一
        CaseTestReport.objects.create(**{
            'name':report_name,
            'case_id': case_list,
            'case_group_id': group_list,
            'report_name': runTaskId,
            'run_cookie': account_id,
            'run_env': env,
            'run_user_nickname': creator,
            'report_status': 0,
            'run_type': 3,#测试计划
            'plan_id':plant_id
        })
        #执行测试任务
        RunGroupCase(group_list, env, account_id, runTaskId)
    except Exception as e:
        logger.error('添加测试任务失败，失败原因：{}'.format(str(e)))
        return
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
@registe_job(task_name='日报提醒')
def ribao_dinggding(ture=None):
    webhooks = eval(manage_models.system_config.objects.get(name='ribao_ding_webhook').ext)
    for webhook in webhooks:
        r = requests.post(webhook, json={
            "at": {
                "atMobiles": [
                             ],
                "atUserIds": [
                             ],
                "isAtAll": True
            },
            "text": {
            "content":"工作日常要记录，日报云效不能忘，各位大哥行行好，不写真的要罚钱！！！"
                },
            "msgtype": "text"
        })
    return



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

# @registe_job(task_name='同步客服钉钉员工列表')
# def from_csms_update_dingding_users():
#     db.close_old_connections()
#     all_db = pymysql.connect(host='mysql.sit.yintaerp.com',
#                              user='yt_csms',
#                              password='thio2ooPhau',
#                              database='yt_csms',
#                              port=3306,
#                              cursorclass=cursors.DictCursor)
#     all_db.set_charset('utf8')
#     all_cursor = all_db.cursor()
#     all_cursor.execute('select * from t_company_staff_data')
#     all_datas = all_cursor.fetchall()  # 主sql查询出来的数据
#     for data in all_datas:
#         mail_list.objects.update_or_create(defaults={
#             'ding_name':data['user_name'],
#             'ding_userid':data['user_id'],
#             'userIcon':data['avatar'],
#             'tapd_name':''.join(lazy_pinyin(data['user_name']))
#         },ding_userid=data['user_id'])

@registe_job(task_name='更新erp账号信息')
def update_erpAccount():
    db.close_old_connections()
    updateToken()#更新账号token
    # account_list = tuple(manage_models.ErpAccount.objects.filter(status=1, is_del=1).values())
    # r = requests.session()
    # for accountquery in account_list:
    #     config_json = accountquery['config_json']
    #     config_id = accountquery['config_id']
    #     try:
    #         env_conf_headers = eval(manage_models.system_config.objects.get(id=config_id).ext.replace('null','None'))['headers']
    #         if config_json:
    #             config_json = eval(config_json)
    #         else:
    #             logger.error('账号配置信息错误')
    #             continue
    #         account_name,method, data, url, content_type = \
    #             accountquery['account_name'],config_json['method'], config_json['login_body'], config_json['login_url'], \
    #             config_json['content-type']
    #         if method == 'GET':
    #             login = r.get(url, params=data)
    #         else:
    #             if content_type == 'data':
    #                 login = r.post(url, data=data)
    #             else:
    #                 login = r.post(url, json=data)
    #         if login.status_code < 400 and (r.cookies or login.json()):
    #             if env_conf_headers and env_conf_headers != {}:
    #                 for key in env_conf_headers.keys():
    #                     if env_conf_headers[key] and env_conf_headers[key][0] != '$':  # 如果headers中的key有值，且开头字符不等于$时，无需特殊处理
    #                         continue
    #                     else:
    #                         if key == 'cookie':
    #                             cookie_dict = requests.utils.dict_from_cookiejar(r.cookies)
    #                             env_conf_headers[key] = ''
    #                             for i in cookie_dict.keys():
    #                                 env_conf_headers[key] += '{}={};'.format(i, cookie_dict[i])
    #                         elif config_id == 44 and key != 'cookie':
    #                             cookie_dict = requests.utils.dict_from_cookiejar(r.cookies)
    #                             env_conf_headers[key] = ''
    #                             for i in cookie_dict.keys():
    #                                 if i == 'token':
    #                                     env_conf_headers[key] = cookie_dict[i]
    #                         else:  # 如果key不为cookie，且没有默认值，则从接口返回值中循环层级取
    #                             relist = env_conf_headers[key][1:].split('.')
    #                             resp = login.json()
    #                             for header_key in relist:
    #                                 resp = resp[header_key]
    #                             if key == 'Authorization':
    #                                 env_conf_headers[key] = 'Bearer ' + resp
    #                             else:
    #                                 env_conf_headers[key] = resp
    #                             logger.info('----------------------------:{}'.format(env_conf_headers,resp))
    #         else:
    #             logger.error('更新cookie数据失败：{}'.format(account_name))
    #             continue
    #         try:
    #             manage_models.ErpAccount.objects.filter(id=accountquery['id']).update(
    #                 headers=env_conf_headers,
    #             )
    #             logger.info(env_conf_headers)
    #             logger.info('更新erp成功：{}'.format(account_name))
    #         except Exception as e:
    #             logger.error('更新cookie数据失败：{},失败原因:{}'.format(account_name, str(e)))
    #             continue
    #     except Exception as e:
    #         logger.error('未获取到cookie，账号account：{}'.format(account_name))
    #         logger.error('{}'.format(e))
    #         continue
    #     r.cookies.clear()  # 清除实例的旧cookie


@registe_job(task_name='每周一删除两周前的抓包数据')
def del_mitm_data():
    db.close_old_connections()
    now = datetime.datetime.now()
    last_last_week = now - datetime.timedelta(hours=2)
    # is_bug不等于1 ，就是已转bug, 不删除
    MitData.objects.filter(created_time__lte=last_last_week).delete()  # gte 大于等于
    logger.info(f"{last_last_week} 之前的数据已删除！")

@registe_job(task_name='mit数据匹配swagger')
def mitForSwagger():
    db.close_old_connections()
    MitQuerys = MitData.objects.filter(env=0)
    for mit_query in MitQuerys:
        try:
            #name
            swagger_querys = SwaggerApi.objects.filter(url=mit_query.url,is_delete=0).exists()
            if swagger_querys:
                mit_query.name = SwaggerApi.objects.get(url=mit_query.url,is_delete=0).api_name
                mit_query.project_id = SwaggerApi.objects.get(url=mit_query.url,is_delete=0).project_id
                mit_query.case_status = SwaggerApi.objects.get(url=mit_query.url,is_delete=0).case_status
            if not swagger_querys:
                project = projectMent.objects.filter(host=mit_query.host_name).exists()
                if project:
                    mit_query.project_id = projectMent.objects.get(host=mit_query.host_name).id
            mit_query.env = 1
            mit_query.plat_module = []
            mit_query.save()
            logger.info('更新成功：{}'.format(mit_query.id))
        except Exception as e:
            logger.error('查询mit对应数据失败，失败原因{}'.format(str(e)))





def return_times():
    times = str(int(time.time() * 1000)) + '.0125'
    return times


def return_time():
    times = str(int(time.time() * 1000))
    return times
