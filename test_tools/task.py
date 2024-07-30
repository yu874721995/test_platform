import json
import time
from urllib.parse import urljoin

from test_plant.task import registe_job
from test_tools.common import reload_cookie, reload_xxjob_cookie
from test_tools import models
from nextop_tapd import models as tapd_models
import datetime
import logging
import django.db as db
from django.utils import timezone
from test_management.common import DateEncoder
from bs4 import BeautifulSoup
from test_tools.common import GitOperationLibraryRemote
from django.db.models import Q
from django.core.paginator import Paginator
from test_tools.common import send_group_msg
from test_tools.common import getDubboAdminToken
from test_case.models import DubboInterFaceService,DubboInterFaceMethod,DubboInterFaceMethodParmes
from django.db import transaction

logger = logging.getLogger(__name__)

bkciHost = 'http://devops.ops.nextop.cc'



@registe_job(task_name='同步流水线构建记录')
def Synchronous_pipelineBuildDetail():
    r = reload_cookie()
    token = r.get(bkciHost + '/ms/auth/api/user/token/get').json()['data']['accessToken']  # 获取token
    projects = r.get(bkciHost + '/ms/openapi/api/apigw/v3/projects?access_token={}'.format(token))  # 获取项目列表
    for project in projects.json()['data']:
        projectCode = project['projectCode']
        if projectCode == 'nextop-saas' or projectCode == 'daily-env':
            continue
        AssemblyList = r.get(
            bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines?access_token={}&&page=1&&pageSize=1000'.format(
                projectCode, token)).json()['data']  # 获取所有流水线
        for Assembly in AssemblyList['records']:
            # 获取构建历史
            build_history = r.get(
                bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/builds/history?access_token={}'.format(
                    projectCode, Assembly['pipelineId'], token)).json()
            for history in build_history['data']['records']:
                try:
                    data = {}
                    historyDetail = {}
                    for item in history['buildParameters']:
                        historyDetail[item['key']] = item['value']
                    data['Assembly_id'] = Assembly['pipelineId']
                    data['build_id'] = history['id']
                    exsit = models.Assembly_build_detail.objects.filter(build_id=history['id']).exists()
                    if exsit:
                        query = models.Assembly_build_detail.objects.get(build_id=history['id'])
                        if query.build_status == 1:
                            logger.info('构建记录已存在且处于已完成状态，无需更新:{}'.format(Assembly['pipelineId']))
                            continue
                    buildDetail = r.get(
                        bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/builds/{}/status?access_token={}'.format(
                            projectCode, Assembly['pipelineId'], history['id'], token)).json()['data']
                    buildTaskDetail = r.get(
                        bkciHost + '/ms/process/api/user/builds/{}/{}/{}/detail'.format(projectCode,
                                                                                        Assembly['pipelineId'],
                                                                                        history['id'])).json()['data'][
                        'model'][
                        'stages']
                    data['build_task'] = None
                    for stage in buildTaskDetail:
                        tasks = stage['containers'][0]['elements']
                        for task in tasks:
                            if task.__contains__('status'):
                                if buildDetail['status'] == 'FAILED' and task['status'] == 'FAILED':
                                    data['build_task'] = task['name']
                                    break
                                else:
                                    data['build_task'] = task['name']

                    if buildDetail['status'] == 'RUNNING' and data['build_task'] in ['最终审核提醒', '测试人员审核',
                                                                                     '测试人员审核是否通过验证']:
                        data['build_status'] = 5
                    elif buildDetail['status'] == 'RUNNING':
                        data['build_status'] = 3
                    elif buildDetail['status'] == 'SUCCEED':
                        data['build_status'] = 1
                    elif buildDetail['status'] == 'FAILED':
                        data['build_status'] = 2
                    elif buildDetail['status'] == 'CANCELED':
                        data['build_status'] = 4
                    else:
                        data['build_status'] = 1

                    data['Assembly_serviceName'] = historyDetail['serviceName'] if historyDetail.__contains__(
                        'serviceName') else None

                    if projectCode != 'production':
                        if projectCode == 'devtest':
                            data['branch'] = historyDetail['branch'] if historyDetail.__contains__('branch') else None
                        else:
                            data['branch'] = historyDetail['branch_list'] if historyDetail.__contains__(
                                'branch_list') else None
                        data['Assembly_serverName'] = historyDetail['server_env'] if historyDetail.__contains__(
                            'server_env') else None
                    else:
                        data['branch'] = 'master'
                        data['Assembly_serverName'] = 'nextop-prod'
                    data['git'] = historyDetail['gitAddr'] if historyDetail.__contains__('gitAddr') else None

                    data['buildBeginTime'] = datetime.datetime.fromtimestamp(history['startTime'] / 1000)
                    data['buildEndTime'] = datetime.datetime.fromtimestamp(
                        history['endTime'] / 1000) if history.__contains__('endTime') else None
                    is_test = True
                    if projectCode == 'devtest':
                        if historyDetail.__contains__('is_test'):
                            if historyDetail['is_test'] == 'false':
                                is_test = False
                    data['build_examine'] = is_test
                    if tapd_models.mail_list.objects.filter(email=history['userId'],ding_status='是').exists():
                        build_man = tapd_models.mail_list.objects.get(email=history['userId'],ding_status='是').ding_name
                    else:
                        build_man = history['userId']
                    data['build_man'] = build_man

                    data['examine_man'] = historyDetail['test_user'] if historyDetail.__contains__(
                        'test_user') else None
                    # 网关，只有联调-前端才取网关地址
                    detail = r.get(
                        bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/builds/{}/logs/after?access_token={}&&tag=e-84740f15643946abbbf163b8f0ec3079'.format(
                            projectCode, Assembly['pipelineId'], history['id'], token)).json()['data']['logs']
                    for log, index in zip(detail, range(len(detail))):
                        if '运行的pod IP地址' in log['message']:
                            try:
                                data['popId'] = detail[index + 1]['message'].split('-----')[1]
                            except Exception as e:
                                data['popId'] = None
                        if projectCode == 'devtest':
                            if '前端Ingress访问IP：' in log['message']:
                                data['gateway_addr'] = log['message'].split('IP：')[1]
                            if '输出日志浏览地址' in log['message']:
                                data['logs_addr'] = detail[index + 1]['message']
                        elif projectCode == 'pre':
                            data['gateway_addr'] = '10.0.0.124'
                            data[
                                'logs_addr'] = 'https://kuboard.nextop.cc/kubernetes/nextop-pre/namespace/nextop-pre/workload/view/Deployment/{}-v1'.format(
                                data['Assembly_serviceName'])
                        elif projectCode == 'production':
                            data['gateway_addr'] = '120.79.147.174'
                            data[
                                'logs_addr'] = 'https://kuboard.nextop.cc/kubernetes/nextop-prod/namespace/nextop-prod/workload/view/Deployment/{}-v1'.format(
                                data['Assembly_serviceName'])
                        else:
                            data['gateway_addr'] = None
                            data['logs_addr'] = None
                    if data['Assembly_serviceName'] == 'nextop-open-api':
                        git = GitOperationLibraryRemote(username='bei.yu', password='Yu19950122.',
                                                        private_token='wF54mooE3NrnaEahUyvV')
                        projects = git.project('nextop-open-api')
                        commits = git.commits(projects[0], ref=data['branch'])
                        data['commit_id'] = commits[0].id
                    data['offline'] = False
                    data['mergeMaster'] = True
                    if projectCode == 'devtest':
                        if historyDetail.__contains__('offline'):
                            data['offline'] = True if historyDetail['offline'] == 'true' else False
                    if projectCode == 'production':
                        if historyDetail.__contains__('mergeMaster'):
                            data['mergeMaster'] = True if historyDetail['mergeMaster'] == 'true' else False
                    logger.info('更新构建记录：{}'.format(data))
                    models.Assembly_build_detail.objects.update_or_create(defaults=data, build_id=data['build_id'])
                except Exception as e:
                    logger.error('流水线构建记录更新失败：{}，--{}'.format(str(e),Assembly['pipelineId']))
                    continue


@registe_job(task_name='同步流水线')
def Synchronous_pipeline():
    r = reload_cookie()
    token = r.get(bkciHost + '/ms/auth/api/user/token/get').json()['data']['accessToken']  # 获取token
    projects = r.get(bkciHost + '/ms/openapi/api/apigw/v3/projects?access_token={}'.format(token))  # 获取项目列表
    allAssemblyIdList = []
    for project in projects.json()['data']:
        projectCode = project['projectCode']
        if projectCode == 'nextop-saas' or projectCode == 'daily-env':
            continue
        AssemblyList = r.get(
            bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines?access_token={}&&page=1&&pageSize=1000'.format(
                projectCode, token)).json()['data']  # 获取所有流水线
        for Assembly in AssemblyList['records']:
            allAssemblyIdList.append(Assembly['pipelineId'])  # 所有流水线id，用于标记被删除的流水线
            try:
                AssemblyDetail = r.get(
                    bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/status?access_token={}'.format(
                        projectCode, Assembly['pipelineId'], token)).json()['data']  # 获取流水线详情
                manualStartupInfo = r.get(
                    bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/builds/manualStartupInfo?access_token={}'.format(
                        projectCode,
                        Assembly['pipelineId'], token)).json()['data']['properties']
                manualStartupInfoJson = {}
                for item in manualStartupInfo:
                    manualStartupInfoJson[item['id']] = item['defaultValue']  # 获取流水线构建默认参数
                if manualStartupInfoJson.__contains__('projectType'):
                    if manualStartupInfoJson['projectType'] == 'web':
                        projectType = 1
                    elif manualStartupInfoJson['projectType'] == 'java':
                        projectType = 2
                    else:
                        projectType = 3
                else:  # projectType为新加字段，旧流水线可能没有
                    if manualStartupInfoJson.__contains__('is_micro'):
                        projectType = 1
                    else:
                        projectType = 2
                latestBuildId = AssemblyDetail['latestBuildId'] if AssemblyDetail.__contains__('latestBuildId') else None
                if not models.Assembly_build_detail.objects.filter(build_id=latestBuildId,
                                                                   Assembly_id=AssemblyDetail['pipelineId']).exists():
                    logger.error('流水线最后一次构建id的构建记录不存在：{}，构建记录:{}--{}'.format(AssemblyDetail['pipelineName'],
                                                                             latestBuildId,
                                                                             AssemblyDetail['pipelineId']))
                    continue
                lastBuildDetail = models.Assembly_build_detail.objects.get(build_id=latestBuildId,
                                                                           Assembly_id=AssemblyDetail['pipelineId'])

                # 关联联调流水线
                old_Assembly_serverName = ''
                if projectCode != 'devtest':
                    dev_Assembly_serverNames = models.Assembly_line.objects.filter(
                        Assembly_serviceName=lastBuildDetail.Assembly_serviceName, project='devtest', status=1).values(
                        'Assembly_serverName')
                    if len(dev_Assembly_serverNames) > 0:
                        for dev_Assembly_serverName in dev_Assembly_serverNames:
                            old_Assembly_serverName += dev_Assembly_serverName['Assembly_serverName']

                # 更新流水线 projectId、pipelineId、pipelineName、
                logger.info('更新流水线成功:{}'.format(AssemblyDetail['pipelineName']))
                models.Assembly_line.objects.update_or_create(defaults={
                    'Assembly_name': AssemblyDetail['pipelineName'],
                    'status': 1,
                    'build_status': lastBuildDetail.build_status,
                    'Assembly_type': projectType,
                    'build_id': AssemblyDetail['latestBuildId'],
                    'project': projectCode,
                    'Assembly_serverName': lastBuildDetail.Assembly_serverName,
                    'Assembly_serviceName': lastBuildDetail.Assembly_serviceName,
                    'branch': lastBuildDetail.branch,
                    'git': lastBuildDetail.git,
                    'build_man': lastBuildDetail.build_man,
                    'buildBeginTime': lastBuildDetail.buildBeginTime,
                    'buildEndTime': lastBuildDetail.buildEndTime,
                    'offline': lastBuildDetail.offline,
                    'mergeMaster': lastBuildDetail.mergeMaster,
                    'logs_addr': lastBuildDetail.logs_addr,
                    'popId': lastBuildDetail.popId,
                    'gateway_addr': lastBuildDetail.gateway_addr,
                    'build_examine': lastBuildDetail.build_examine,
                    'build_task': lastBuildDetail.build_task,
                    'old_Assembly_serverName': old_Assembly_serverName,
                    'examine_man': lastBuildDetail.examine_man,
                    'commit_id': lastBuildDetail.commit_id,
                    'updateTime': timezone.now()
                }, Assembly_id=AssemblyDetail['pipelineId'])
            except Exception as e:
                logger.error('更新流水线失败：{}'.format(str(e),Assembly['pipelineId']))
    models.Assembly_line.objects.filter().exclude(Assembly_id__in=allAssemblyIdList).update(status=2)


@registe_job(task_name='同步所有xxjob')
def Synchronous_xxjob():
    db.close_old_connections()
    envs = ['test', 'pre']
    for env in envs:
        if env == 'test':
            r = reload_xxjob_cookie('test')
            host = 'http://xxl-job-admin.erp-sit.yintaerp.com'
        else:
            r = reload_xxjob_cookie('pre')
            host = 'http://xxl-job-admin.erp-uat.yintaerp.com'
        url = urljoin(host, 'xxl-job-admin/jobinfo')
        group_list_heml = r.get(url).text
        soup = BeautifulSoup(group_list_heml)
        options = soup.find_all(attrs={'id': 'jobGroup'})[0].find_all('option')
        for option in options:
            try:
                data = {}
                if env == 'test':
                    data['env'] = 1
                else:
                    data['env'] = 2
                data['group_id'] = int(option['value'])
                data['group_name'] = option.text
                page_url = urljoin(host, 'xxl-job-admin/jobinfo/pageList')
                page_data = {
                    'jobGroup': data['group_id'],
                    'triggerStatus': -1,
                    'jobDesc': '',
                    'executorHandler': '',
                    'author': '',
                    'start': 0,
                    'length': 100
                }
                pagersp = r.post(page_url, data=page_data)
                if pagersp.status_code != 200:
                    logger.error('{}更新xxjob失败'.format(data['group_name']))
                    continue
                pageJson = pagersp.json()['data']
                logger.info('env:{},group_name:{},jobNum:{}'.format(env, data['group_name'], len(pageJson)))
                if len(pageJson) == 0:
                    logger.error('{}任务组没有任务'.format(data['group_name']))
                    continue
                for page in pageJson:
                    data['job_id'] = page['id']
                    data['job_status'] = 1 if page['triggerStatus'] == 1 else 2
                    data['job_name'] = page['jobDesc']
                    data['job_owner'] = page['author']
                    data['job_parmes'] = page['executorParam']
                    p_url = urljoin(host, 'xxl-job-admin/jobgroup/loadById')
                    poplist = r.post(p_url.format(env), data=
                    'id={}'.format(data['group_id'])
                                     , verify=False)
                    pop = poplist.json()['content']['registryList']
                    data['job_popid_list'] = pop
                    models.xxjobMenu.objects.update_or_create(defaults=data, job_id=data['job_id'], env=data['env'])
            except Exception as e:
                logger.error('更新xxjob失败：{}'.format(str(e)))
                continue

@registe_job(task_name='同步所有dubbo接口')
def synchronous_dubbo():
    db.close_old_connections()
    r = getDubboAdminToken()
    # 第一个版本先固定1000条，暂时够用了
    serviceListUrl = 'https://dubbo-admin.erp-sit.yintaerp.com/api/dev/service?pattern=service&filter=*&page=0&size=1000'
    serviceListRep = r.get(serviceListUrl).json()
    for content in serviceListRep['content']:
        with transaction.atomic():
            save_id = transaction.savepoint()
            try:
                serviceData = getServiceMethod(r, content)
                logger.info(serviceData)
                interfaceDate = serviceData['interfaceDate']
                methodData = serviceData['methodDate']
                interface,isCreated = DubboInterFaceService.objects.update_or_create(
                    defaults=interfaceDate,
                    serviceName=interfaceDate['serviceName'],
                    InterFaceService=interfaceDate['InterFaceService'])
                interfaceId = interface.id
                if methodData:
                    for method in methodData:
                        method['interfaceId'] = interfaceId
                        parmesList = method['parmesList']
                        method.pop('parmesList')
                        methodQuery,created = DubboInterFaceMethod.objects.update_or_create(
                            defaults=method,
                            interfaceId=interfaceId,
                            methodName=method['methodName']
                        )
                        if parmesList:
                            for parme in parmesList:
                                parme['methodId'] = methodQuery.id
                                DubboInterFaceMethodParmes.objects.update_or_create(
                                    defaults=parme,
                                    parmesNameEn = parme['parmesNameEn'],
                                    methodId = methodQuery.id
                                )
            except json.decoder.JSONDecodeError as e:
                logging.error('errormsg:{}'.format(str(e)))
                transaction.savepoint_rollback(save_id)
                continue


def updateBuildStauts(Assembly_id, status, Build_id):
    beginTime = int(time.time())
    maxTime = 60 * 60 * 24
    while int(time.time()) < (beginTime + maxTime):
        r = reload_cookie()
        time.sleep(3)
        projectExists = models.Assembly_line.objects.filter(Assembly_id=Assembly_id).exists()
        token = r.get(bkciHost + '/ms/auth/api/user/token/get').json()['data']['accessToken']  # 获取token
        if projectExists:
            data = {}
            try:
                projectCode = models.Assembly_line.objects.get(Assembly_id=Assembly_id).project
                buildDetail = r.get(
                    bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/builds/{}/status?access_token={}'.format(
                        projectCode, Assembly_id, Build_id, token)).json()['data']
                buildParmes = {}
                for item in buildDetail['buildParameters']:
                    buildParmes[item['key']] = item['value']
                data['Assembly_id'] = Assembly_id
                buildTaskDetail = r.get(
                    bkciHost + '/ms/process/api/user/builds/{}/{}/{}/detail'.format(projectCode, Assembly_id,
                                                                                    Build_id)).json()['data']['model'][
                    'stages']
                data['build_task'] = None
                for stage in buildTaskDetail:
                    tasks = stage['containers'][0]['elements']
                    for task in tasks:
                        if task.__contains__('status'):
                            if buildDetail['status'] == 'FAILED' and task['status'] == 'FAILED':
                                data['build_task'] = task['name']
                                break
                            else:
                                data['build_task'] = task['name']
                data['Assembly_serviceName'] = buildParmes['serviceName']
                data['Assembly_serverName'] = buildParmes['server_env'] if buildParmes.__contains__(
                    'server_env') else 'nextop-prod'
                if projectCode == 'production':
                    data['branch'] = 'master'
                elif projectCode == 'pre':
                    data['branch'] = buildParmes['branch_list']
                else:
                    data['branch'] = buildParmes['branch']
                data['git'] = buildParmes['gitAddr']

                if tapd_models.mail_list.objects.filter(email=buildDetail['userId'],ding_status='是').exists():
                    build_man = tapd_models.mail_list.objects.get(email=buildDetail['userId'],ding_status='是').ding_name
                else:
                    build_man = buildDetail['userId']
                data['build_man'] = build_man
                data['buildBeginTime'] = datetime.datetime.fromtimestamp(buildDetail['startTime'] / 1000)
                data['buildEndTime'] = datetime.datetime.fromtimestamp(
                    buildDetail['endTime'] / 1000) if buildDetail.__contains__('endTime') else None
                data['build_id'] = Build_id
                if projectCode == 'devtest':
                    data['offline'] = True if buildParmes['offline'] == 'true' else False
                    data['build_examine'] = False if buildParmes['is_test'] == 'false' else True
                else:
                    data['offline'] = False
                    data['build_examine'] = True
                if projectCode == 'production':
                    data['mergeMaster'] = True if buildParmes['mergeMaster'] == 'true' else False
                detail = r.get(
                    bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/builds/{}/logs/after?access_token={}&&tag=e-84740f15643946abbbf163b8f0ec3079'.format(
                        projectCode, Assembly_id, Build_id, token)).json()['data']['logs']
                for log, index in zip(detail, range(len(detail))):
                    if '运行的pod IP地址' in log['message']:
                        try:
                            data['popId'] = detail[index + 1]['message'].split('-----')[1]
                        except Exception as e:
                            data['popId'] = None
                    if projectCode == 'devtest':
                        if '前端Ingress访问IP：' in log['message']:
                            data['gateway_addr'] = log['message'].split('IP：')[1]
                        if '输出日志浏览地址' in log['message']:
                            data['logs_addr'] = detail[index + 1]['message']
                    elif projectCode == 'pre':
                        data['gateway_addr'] = '10.0.0.124'
                        data[
                            'logs_addr'] = 'https://kuboard.nextop.cc/kubernetes/nextop-pre/namespace/nextop-pre/workload/view/Deployment/{}-v1'.format(
                            data['Assembly_serviceName'])
                    elif projectCode == 'production':
                        data['gateway_addr'] = '120.79.147.174'
                        data[
                            'logs_addr'] = 'https://kuboard.nextop.cc/kubernetes/nextop-prod/namespace/nextop-prod/workload/view/Deployment/{}-v1'.format(
                            data['Assembly_serviceName'])
                    else:
                        data['gateway_addr'] = None
                        data['logs_addr'] = None
                data['examine_man'] = buildParmes['test_user'] if buildParmes.__contains__('test_user') else None
                if data['Assembly_serviceName'] == 'nextop-open-api':
                    git = GitOperationLibraryRemote(username='bei.yu', password='Yu19950122.',
                                                    private_token='wF54mooE3NrnaEahUyvV')
                    projects = git.project('nextop-open-api')
                    commits = git.commits(projects[0], ref=data['branch'])
                    data['commit_id'] = commits[0].id

                if buildDetail['status'] == 'RUNNING' and data['build_task'] in ['最终审核提醒', '测试人员审核', '测试人员审核是否通过验证']:
                    data['build_status'] = 5
                elif buildDetail['status'] == 'RUNNING':
                    data['build_status'] = 3
                elif buildDetail['status'] == 'SUCCEED':
                    data['build_status'] = 1
                elif buildDetail['status'] == 'FAILED':
                    data['build_status'] = 2
                elif buildDetail['status'] == 'CANCELED':
                    data['build_status'] = 4
                else:
                    data['build_status'] = 1
                models.Assembly_build_detail.objects.update_or_create(defaults=data, Assembly_id=Assembly_id,
                                                                      build_id=Build_id)
                data['update_time'] = timezone.now()
                # 关联联调流水线
                if projectCode != 'devtest':
                    dev_Assembly_serverNames = models.Assembly_line.objects.filter(
                        Assembly_serviceName=data['Assembly_serviceName'], project='devtest', status=1).values(
                        'Assembly_serverName')
                    data['old_Assembly_serverName'] = ''
                    if len(dev_Assembly_serverNames) > 0:
                        for dev_Assembly_serverName in dev_Assembly_serverNames:
                            data['old_Assembly_serverName'] += dev_Assembly_serverName['Assembly_serverName']
                models.Assembly_line.objects.update_or_create(defaults=data, Assembly_id=Assembly_id)
                if buildDetail['status'] in ['FAILED', 'SUCCEED', 'CANCELED']:
                    break
            except Exception as e:
                logger.error('监听失败，错误原因：{}'.format(str(e)))
                break
        else:
            try:
                for project in ['devtest', 'pre', 'production']:
                    AssemblyJson = r.get(
                        bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/status?access_token={}'.format(
                            project, Assembly_id, token)).json()
                    if AssemblyJson.__contains__('data'):
                        AssemblyDetail = AssemblyJson['data']

                        manualStartupInfo = r.get(
                            bkciHost + '/ms/openapi/api/apigw/v3/projects/{}/pipelines/{}/builds/manualStartupInfo?access_token={}'.format(
                                AssemblyDetail['projectId'], Assembly_id, token)).json()['data']['properties']
                        manualStartupInfoJson = {}
                        for item in manualStartupInfo:
                            manualStartupInfoJson[item['id']] = item['defaultValue']  # 获取流水线构建默认参数
                        if manualStartupInfoJson.__contains__('projectType'):
                            if manualStartupInfoJson['projectType'] == 'web':
                                projectType = 1
                            elif manualStartupInfoJson['projectType'] == 'java':
                                projectType = 2
                            else:
                                projectType = 3
                        else:  # projectType为新加字段，旧流水线可能没有
                            if manualStartupInfoJson.__contains__('is_micro'):
                                projectType = 1
                            else:
                                projectType = 2

                        models.Assembly_line.objects.update_or_create(defaults={
                            'Assembly_name': AssemblyDetail['pipelineName'],
                            'status': 1,
                            'Assembly_type': projectType,
                            'build_id': AssemblyDetail['latestBuildId'] if AssemblyDetail.__contains__(
                                'latestBuildId') else None,
                            'project': AssemblyDetail['projectId'],
                            'updateTime': timezone.now()
                        }, Assembly_id=AssemblyDetail['pipelineId'])
            except Exception as e:
                logger.error('监听任务新增流水线失败：{}'.format(str(e)))
                break


def websocketPage(arg, room_name):
    page = arg['page'] if arg.__contains__('page') else 1
    limit = arg['limit'] if arg.__contains__('limit') else 20
    Assembly_name = arg['Assembly_name'] if arg.__contains__('Assembly_name') else None
    Assembly_serviceName = arg['Assembly_serviceName'] if arg.__contains__('Assembly_serviceName') else None
    Assembly_serverName = arg['Assembly_serverName'] if arg.__contains__('Assembly_serverName') else None
    branch = arg['branch'] if arg.__contains__('branch') else None
    Assembly_type = arg['Assembly_type'] if arg.__contains__('Assembly_type') else None
    build_man = arg['build_man'] if arg.__contains__('build_man') else None
    project = arg['project'] if arg.__contains__('project') else None
    build_status = arg['build_status'] if arg.__contains__('build_status') else None
    query = Q(status=1)
    if Assembly_name:
        query &= Q(Assembly_name__icontains=Assembly_name)
    if Assembly_serviceName:
        query &= Q(Assembly_serviceName__icontains=Assembly_serviceName)
    if Assembly_serverName:
        if project != 'devtest':
            query &= Q(old_Assembly_serverName__icontains=Assembly_serverName)
        else:
            query &= Q(Assembly_serverName__icontains=Assembly_serverName)
    if build_man:
        query &= Q(build_man__icontains=build_man)
    if project:
        query &= Q(project=project)
    if build_status:
        query &= Q(build_status=build_status)
    if Assembly_type:
        query &= Q(Assembly_type=Assembly_type)
    if branch:
        query &= Q(branch__icontains=branch)
    querys = list(models.Assembly_line.objects.filter(query).values().order_by('-buildBeginTime'))
    p = Paginator(querys, limit)  # 实例化分页对象
    logging.info('定时任务查询总数{}'.format(p.count))
    result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
    send_group_msg(room_name, json.loads(json.dumps(result, cls=DateEncoder, ensure_ascii=False)))

def getServiceMethod(r,content):
    service = content['service']
    if not content['group']:
        if content['version']:
            serviceDetailUrl = 'https://dubbo-admin.erp-sit.yintaerp.com/api/dev/service/{}:{}'.format(service, content[
                'version'])
        else:
            serviceDetailUrl = 'https://dubbo-admin.erp-sit.yintaerp.com/api/dev/service/{}'.format(service)
        serviceDetailRep = r.get(serviceDetailUrl).json()
    else:
        if content['version']:
            serviceDetailUrl = 'https://dubbo-admin.erp-sit.yintaerp.com/api/dev/service/{}*{}:{}'.format(content['group'],service, content[
                'version'])
        else:
            serviceDetailUrl = 'https://dubbo-admin.erp-sit.yintaerp.com/api/dev/service/{}*{}'.format(content['group'],service)
        serviceDetailRep = r.get(serviceDetailUrl).json()
    providers = serviceDetailRep['providers'] if serviceDetailRep.__contains__('providers') else []
    data = {
        'interfaceDate':{
            "serviceName":content['appName'],
            "InterFaceService":content['service'],
            "providers":providers,
            "version":content['version'],
            "group":content['group']
        },
        'methodDate':[]
    }
    # 获取serviceMethodDetail
    try:
        serviceMethodDetailUrl = 'https://dubbo-admin.erp-sit.yintaerp.com/api/dev/docs/apiModuleList?dubboIp={}&dubboPort={}'.format(
            providers[0]['address'].split(':')[0],providers[0]['address'].split(':')[1]
        )
        # serviceMethodDetailUrl = 'https://dubbo-admin.erp-sit.yintaerp.com/api/dev/docs/apiModuleList?dubboIp={}&dubboPort={}'.format(
        #     '192.168.3.202', 31281
        # )
        serviceMethodrsp = r.get(serviceMethodDetailUrl)
        serviceMethodDetail = json.loads(serviceMethodrsp.text)
        serviceMethodDetail = eval(serviceMethodDetail.replace('null', 'None').replace('false', 'False').replace('true', 'True'))
        for module in serviceMethodDetail:
            for method in module['moduleApiList']:
                methodDict = {}
                apiName = '{}.{}{}'.format(module['moduleClassName'],method['apiName'],method['paramsDesc'])
                methodParmesUrl = 'https://dubbo-admin.erp-sit.yintaerp.com/api/dev/docs/apiParamsResp'
                methodParmesRsp = r.get(methodParmesUrl,params={
                    'dubboIp':providers[0]['address'].split(':')[0],
                    'dubboPort':providers[0]['address'].split(':')[1],
                    'apiName':apiName
                })
                methodParmesDetail = json.loads(methodParmesRsp.text)
                methodParmesDetail = eval(
                    methodParmesDetail.replace('null', 'None').replace('false', 'False').replace('true', 'True'))
                methodDict['serviceName'] = content['appName']
                methodDict['InterFaceService'] = content['service']
                methodDict['moduleDocName'] = module['moduleClassName']
                methodDict['methodName'] = method['apiDocName']
                methodDict['methodNamedocs'] = method['apiRespDec']
                methodDict['version'] = content['version']
                methodDict['group'] = content['group']
                methodDict['parmesType'] = methodParmesDetail['methodParamInfo']
                methodDict['paramsDesc'] = method['paramsDesc']
                methodDict['parmesList'] = []
                for parmes in methodParmesDetail['params']:
                    for parme in parmes['paramInfo']:
                        parmesDate = {
                            'parmesNameEn':parme['name'],
                            'parmesNameZn':parme['docName'],
                            'parmesText':parme['subParamsJson'],
                            'javaType':parme['javaType'],
                            'required':parme['required'],
                            'description':parme['description']
                        }
                        methodDict['parmesList'].append(parmesDate)
                data['methodDate'].append(methodDict)
    except Exception as e:
        logging.info('获取parmes失败，未维护docs文档，尝试单独获取method')
        logging.error('内部error:{}'.format(str(e)))
        if serviceDetailRep['metadata'] and serviceDetailRep['metadata'].__contains__('methods'):
            if serviceDetailRep['metadata']['methods']:
                for method in serviceDetailRep['metadata']['methods']:
                    methodDict = {}
                    methodDict['serviceName'] = content['appName']
                    methodDict['InterFaceService'] = content['service']
                    methodDict['methodName'] = method['name']
                    methodDict['methodNamedocs'] = method['name']
                    methodDict['version'] = content['version']
                    methodDict['group'] = content['group']
                    methodDict['parmesType'] = method['parameterTypes'][0] if method['parameterTypes'] else None
                    methodDict['parmesList'] = []
                    data['methodDate'].append(methodDict)
    return data