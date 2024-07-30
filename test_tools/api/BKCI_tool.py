import logging
from test_plant import models
from django.http import HttpResponse
from django.core.paginator import Paginator
import datetime
from test_tools import models
from test_tools.common import reload_cookie, keys, checkBuild, Audit, build
from django.utils import timezone
from test_management.common import json_request, DateEncoder, jwt_token, request_verify
from django.db.models import Q
from test_tools.task import updateBuildStauts
from test_plant.task import scheduler
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from test_tools.jenkins_task import websocketPage
from test_plant.common import add_job
from django_apscheduler.models import DjangoJob

logger = logging.getLogger(__name__)


class BkCiToolView():

    @classmethod
    @request_verify('post')
    def List(cls, request):
        page = json_request(request, 'page', int, not_null=False, default=1)
        limit = json_request(request, 'limit', int, not_null=False, default=20)
        Assembly_name = json_request(request, 'Assembly_name', str, not_null=False, default=None)
        Assembly_serviceName = json_request(request, 'Assembly_serviceName', str, not_null=False, default=None)
        Assembly_serverName = json_request(request, 'Assembly_serverName', str, not_null=False, default=None)
        branch = json_request(request, 'branch', str, not_null=False, default=None)
        Assembly_type = json_request(request, 'Assembly_type', int, not_null=False, default=None)
        build_man = json_request(request, 'build_man', str, not_null=False, default=None)
        project = json_request(request, 'project', str, not_null=False, default=None)
        build_status = json_request(request, 'build_status', int, not_null=False, default=None)
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
    @request_verify('post', {'Assembly_id': str, 'status': int, 'build_id': str})
    def bkci_Callback(cls, request):
        Assembly_id = json_request(request, 'Assembly_id', str, not_null=False, default=None)
        status = json_request(request, 'status', int, not_null=False, default=None)
        build_id = json_request(request, 'build_id', str, not_null=False, default=None)
        try:
            if status == 3:
                scheduler.add_job(updateBuildStauts, 'date', run_date=timezone.now(),
                                  id='updateBuildStauts_{}'.format(build_id), args=[Assembly_id, status, build_id])
        except Exception as e:
            logger.error('开始监听构建状态失败:{}'.format(str(e)))
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '开始监听构建状态失败:{}'.format(str(e))
            }))
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    @request_verify('post', {'Assembly_list': list, 'userKey': str, 'status': int})
    def to_examine(cls, request):
        username = jwt_token(request)['email']
        Assembly_list = json_request(request, 'Assembly_list', list, not_null=False, default=None)
        userKey = json_request(request, 'userKey', str, not_null=False, default=None)
        userKey = keys(userKey)
        status = json_request(request, 'status', int, not_null=False, default=None)
        r = reload_cookie(username, userKey)
        querys = models.Assembly_line.objects.filter(Assembly_id__in=Assembly_list).values()
        if status == 1:
            examine_status = 'PROCESS'
        else:
            examine_status = 'ABORT'
        examineList = []
        for query in querys:
            Assembly_name = query['Assembly_name']
            Assembly_status = query['status']
            if Assembly_status != 1:
                examineList.append({'name': Assembly_name, 'status': 2, 'msg': '流水线已被删除'})
                continue
            try:
                Audit(r, query, examine_status)
                examineList.append({'name': Assembly_name, 'status': 1, 'msg': '审核成功'})
            except Exception as e:
                logger.error('审核流水线失败：{}'.format(str(e)))
                examineList.append({'name': Assembly_name, 'status': 2, 'msg': '查询流水线关联数据失败'})
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功',
            'data': examineList
        }))

    @classmethod
    @request_verify('post', {'Assembly_list': list, 'userKey': str})
    def structure(cls, request):
        username = jwt_token(request)['email']
        userKey = json_request(request, 'userKey', str, not_null=False, default=None)
        userKey = keys(userKey)
        r = reload_cookie(username, userKey)
        Assembly_list = json_request(request, 'Assembly_list', list, not_null=False, default=None)
        structureList = []
        waitting_Assembly_id = None
        for Assembly in Assembly_list:
            Assembly_id = Assembly['Assembly_id']
            Assembly_name = models.Assembly_line.objects.get(Assembly_id=Assembly_id).Assembly_name
            build_status = models.Assembly_line.objects.get(Assembly_id=Assembly_id).build_status
            Assembly_status = models.Assembly_line.objects.get(Assembly_id=Assembly_id).status
            if Assembly_status != 1:
                structureList.append({'name': Assembly_name, 'status': 2, 'msg': '流水线已被删除'})
                continue
            if build_status == 3 or build_status == 5:
                structureList.append({'name': Assembly_name, 'status': 2, 'msg': '该流水线已处于构建中'})
                continue
            is_checkBuild = Assembly['is_checkBuild']  # 阻塞构建0、不需要，1、正常时build，2、待审核build，3、均可或
            is_checkAudit = Assembly['is_checkAudit']  # 是否自动审核
            if waitting_Assembly_id == None and is_checkBuild != 0:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '第一个流水线不允许阻塞'
                }))
            if Assembly['build_examine'] == False and is_checkAudit == True:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '无需审核的流水线不允许开启自动审核'
                }))
            if is_checkBuild != 0:
                scheduler.add_job(checkBuild, run_date=timezone.now(), id=Assembly['Assembly_id'] + '_build_now',
                                  args=[r, waitting_Assembly_id, is_checkBuild, Assembly, is_checkAudit])
                logger.info('添加流水线到阻塞发布列表中：{}'.format(Assembly_name))
                structureList.append({'name': Assembly_name, 'status': 1, 'msg': '等待前一流水线构建'})
                continue
            try:
                if build(r, Assembly, is_checkAudit):
                    structureList.append({'name': Assembly_name, 'status': 1, 'msg': '开始构建成功'})
            except Exception as e:
                structureList.append({'name': Assembly_name, 'status': 2, 'msg': '开始构建失败:{}'.format(str(e))})
            waitting_Assembly_id = Assembly_id
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功',
            'data': structureList
        }))

    @classmethod
    @request_verify('post', {'Assembly': dict, 'userKey': str})
    def offline(cls, request):
        Assembly = json_request(request, 'Assembly', dict, not_null=False, default=None)
        username = jwt_token(request)['email']
        userKey = json_request(request, 'userKey', str, not_null=False, default=None)
        userKey = keys(userKey)
        r = reload_cookie(username, userKey)
        Assembly_id = Assembly['Assembly_id']
        Assembly_type = models.Assembly_line.objects.get(Assembly_id=Assembly_id).Assembly_type
        Assembly_status = models.Assembly_line.objects.get(Assembly_id=Assembly_id).status
        if Assembly_status != 1:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '流水线已被删除'
            }))
        env = models.Assembly_line.objects.get(Assembly_id=Assembly_id).project
        url = 'http://devops.ops.nextop.cc/ms/process/api/user/builds/{}/{}'.format(env, Assembly_id)
        if env == 'production':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '别瞎搞哦,生产流水线不允许下线！'
            }))
        data = {}
        if Assembly_type == 2:
            data['BK_CI_BUILD_MSG'] = '0'
            data['BK_CI_FIX_VERSION'] = '0'
            data['BK_CI_MAJOR_VERSION'] = '0'
            data['BK_CI_MINOR_VERSION'] = '0'
            data['auto_deploy'] = False
            data['branch'] = Assembly['branch']
            data['create_nacos_ns'] = False
            data['get_jacoco'] = True
            data['gitAddr'] = Assembly['git']
            data['is_download'] = False
            data['is_test'] = Assembly['build_examine']
            data['offline'] = True
            data['projectType'] = 'java'
            data['server_env'] = Assembly['Assembly_serverName']
            data['serviceName'] = Assembly['Assembly_serviceName']
            data['test_user'] = Assembly['examine_man']
            data['uploadJar'] = False
            data['uploadSwaggerApi'] = True
            data['upload_main_pom'] = False
        else:
            data['BK_CI_BUILD_MSG'] = ''
            data['BK_CI_FIX_VERSION'] = '0'
            data['BK_CI_MAJOR_VERSION'] = '0'
            data['BK_CI_MINOR_VERSION'] = '0'
            data['auto_deploy'] = False
            data['branch'] = Assembly['branch']
            data['gitAddr'] = Assembly['git']
            data['is_micro'] = True
            data['is_test'] = Assembly['build_examine']
            data['offline'] = True
            data['projectType'] = "web"
            data['server_env'] = Assembly['Assembly_serverName']
            data['serviceName'] = Assembly['Assembly_serviceName']
            data['test_user'] = Assembly['examine_man']
        structureJson = r.post(url, json=data)
        if structureJson.status_code == 200:
            return HttpResponse(json.dumps({
                'code': 10000,
                'msg': '下线构建成功'
            }))
        else:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '下线构建失败'
            }))

    @classmethod
    @request_verify('post', {'AssemblyId_list': list})
    def dev_seach_pre(self, request):
        AssemblyId_list = json_request(request, 'AssemblyId_list', list, not_null=False, default=None)
        querys = models.Assembly_line.objects.filter(Assembly_id__in=AssemblyId_list).values()
        data = []
        for query in querys:
            if query['project'] != 'devtest':
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '包含非联调环境流水线，不允许上预发'
                }))
            exist = models.Assembly_line.objects.filter(project='pre',
                                                        Assembly_serviceName=query['Assembly_serviceName']).exists()
            if not exist:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '包含未创建预发流水线的联调流水线，无法查询：{}'.format(query['Assembly_name'])
                }))
            pre_Assembly = models.Assembly_line.objects.filter(project='pre', Assembly_serviceName=query[
                'Assembly_serviceName']).values()[0]
            data.append(pre_Assembly)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功',
            'data': data
        }, cls=DateEncoder))

    @classmethod
    @request_verify('post', {'AssemblyId_list': list})
    def updateAssembly(self, request):
        r = reload_cookie()
        AssemblyId_list = json_request(request, 'AssemblyId_list', list, not_null=False, default=None)
        querys = models.Assembly_line.objects.filter(Assembly_id__in=AssemblyId_list).values()
        structureList = []
        for query in querys:
            data = {}
            data['project'] = query['project']
            data['Assembly_id'] = query['Assembly_id']
            data['Assembly_name'] = query['Assembly_name']
            try:
                if query['status'] == 2:
                    structureList.append({'name': data['Assembly_name'], 'status': 2, 'msg': '已删除的流水线不允许更新'})
                    continue
                Assembly_history = r.get(
                    'http://devops.ops.nextop.cc/ms/process/api/user/pipelines/projects/{}/listViewPipelines?viewId=allPipeline&projectId={}&page=1&pageSize=60&sortType=UPDATE_TIME&filterByPipelineName={}'.format(
                        data['project'], data['project'], data['Assembly_name'])).json()['data']['records']

                if len(Assembly_history) == 1:
                    Assembly_data = Assembly_history[0]
                else:
                    Assembly_data = Assembly_history[0]
                    for history in Assembly_history:
                        if history['pipelineId'] == data['Assembly_id']:
                            Assembly_data = history
                            break
                build_id = Assembly_data['latestBuildId']
                text = ['最终审核提醒', 'Clean_Job#3(VM)', '测试人员审核', '测试人员审核是否通过验证']
                if Assembly_data['latestBuildStatus'] == 'RUNNING' and Assembly_data['latestBuildTaskName'] in text:
                    data['build_status'] = 5
                elif Assembly_data['latestBuildStatus'] == 'RUNNING':
                    data['build_status'] = 3
                elif Assembly_data['latestBuildStatus'] == 'SUCCEED':
                    data['build_status'] = 1
                elif Assembly_data['latestBuildStatus'] == 'FAILED':
                    data['build_status'] = 2
                elif Assembly_data['latestBuildStatus'] == 'CANCELED':
                    data['build_status'] = 4
                else:
                    data['build_status'] = 1

                detail = r.get('http://devops.ops.nextop.cc/ms/process/api/user/builds/{}/{}/{}/detail'.format(
                    data['project'], data['Assembly_id'], build_id)).json()['data']
                data['build_man'] = Assembly_data['latestBuildUserId']
                data['build_id'] = build_id
                data['build_Time'] = datetime.datetime.fromtimestamp(Assembly_data['latestBuildStartTime'] / 1000)
                manualStartupInfo = r.get(
                    'http://devops.ops.nextop.cc/ms/process/api/user/builds/{}/{}/manualStartupInfo'.format(
                        data['project'], data['Assembly_id'])).json()['data']['properties']
                manualStartupInfoJson = {}
                for item in manualStartupInfo:
                    manualStartupInfoJson[item['id']] = item['defaultValue']
                if data['project'] == 'devtest':
                    data['branch'] = manualStartupInfoJson['branch']
                elif data['project'] == 'pre':
                    data['branch'] = manualStartupInfoJson['branch_list']
                else:
                    data['branch'] = 'master'
                data['Assembly_serviceName'] = manualStartupInfoJson['serviceName']
                if data['project'] == 'production':
                    data['Assembly_serverName'] = 'nextop-prod'
                    data['examine_man'] = ''
                else:
                    data['Assembly_serverName'] = manualStartupInfoJson['server_env']
                    data['examine_man'] = manualStartupInfoJson['test_user']
                data['git'] = manualStartupInfoJson['gitAddr']
                data['build_examine'] = True
                AssemblyParams = detail['model']['stages'][0]['containers'][0]['params']
                AssemblyParamsJson = {}
                for AssemblyParam in AssemblyParams:
                    AssemblyParamsJson[AssemblyParam['id']] = AssemblyParam['defaultValue']
                # 判断是前端流水线还是后端流水线
                if AssemblyParamsJson.__contains__('projectType'):
                    if AssemblyParamsJson['projectType'] == 'web':
                        data['Assembly_type'] = 1
                    elif AssemblyParamsJson['projectType'] == 'java':
                        data['Assembly_type'] = 2
                    else:
                        data['Assembly_type'] = 3
                else:  # projectType为新加字段，旧流水线可能没有
                    if AssemblyParamsJson.__contains__('nacos_addr'):
                        data['Assembly_type'] = 1
                    else:
                        data['Assembly_type'] = 2

                # 只有最新一次构建成功或者走到待审核那一步才更新构建相关信息
                try:
                    if data['Assembly_type'] == 2:  # 后端工程
                        stages = detail['model']['stages']
                        if len(stages) == 3:  # 后端流水线
                            tag_id = detail['model']['stages'][2]['containers'][0][
                                'elements'][2]['id']
                            build_detail = r.get(
                                'http://devops.ops.nextop.cc/ms/ms/log/api/user/logs/{}/{}/{}?tag={}&executeCount=1&subTag=&debug=false'.format(
                                    data['project'], data['Assembly_id'], build_id, tag_id)).json()['data']['logs']
                            if data['project'] == 'devtest':
                                for log, index in zip(build_detail, range(len(build_detail))):
                                    if '前端Ingress访问IP：' in log['message']:
                                        data['gateway_addr'] = log['message'].split('IP：')[1]
                                    if '运行的pod IP地址' in log['message']:
                                        data['popId'] = build_detail[index + 1]['message'].split('-----')[1]
                                    if '输出日志浏览地址' in log['message']:
                                        data['logs_addr'] = build_detail[index + 1]['message']
                except Exception as e:
                    structureList.append({'name': data['Assembly_name'], 'status': 2, 'msg': '更新失败:{}'.format(str(e))})
                    continue
            except Exception as e:
                structureList.append({'name': data['Assembly_name'], 'status': 2, 'msg': '更新失败:{}'.format(str(e))})
                continue
            try:
                dev_Assembly_serverNames = models.Assembly_line.objects.filter(
                    Assembly_serviceName=data['Assembly_serviceName'], project='devtest', status=1).values(
                    'Assembly_serverName')
                data['old_Assembly_serverName'] = ''
                if len(dev_Assembly_serverNames) > 0:
                    for dev_Assembly_serverName in dev_Assembly_serverNames:
                        data['old_Assembly_serverName'] += dev_Assembly_serverName['Assembly_serverName']
            except Exception as e:
                structureList.append({'name': data['Assembly_name'], 'status': 2, 'msg': '更新失败:{}'.format(str(e))})
                continue
            for key, value in data.items():
                if isinstance(value, str):
                    data[key] = value.replace(' ', '').replace(f'\n', '').replace(f'\r', '').replace(f'\t', '')
            models.Assembly_line.objects.update_or_create(defaults=data, Assembly_id=data['Assembly_id'])
            structureList.append({'name': data['Assembly_name'], 'status': 1, 'msg': '更新成功'})
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功',
            'data': structureList
        }, cls=DateEncoder))


# websocket消费者类
class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            self.userId = self.scope['user_id']
            self.nickname = self.scope['username']
            self.room_name = self.userId
            self.room_group_name = 'notice_%s' % self.room_name  # 直接从用户指定的房间名称构造Channels组名称，不进行任何引用或转义。

            # 将新的连接加入到群组
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name)

            await self.accept()
            logger.info('websocket链接成功，连接用户:{}'.format(self.nickname))
        except Exception as e:
            logger.error(str(e))
            await self.close()
            await self.disconnect(1007)

    async def disconnect(self, close_code):  # 断开时触发
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name)
        if DjangoJob.objects.filter(id='web_socket_push_{}'.format(self.userId)).exists(): #断开连接时清除任务
            scheduler.remove_job('web_socket_push_{}'.format(self.userId))

    async def receive(self, text_data=None, bytes_data=None):  # 接收消息时触发
        text_data_json = eval(json.loads(text_data))
        message = text_data_json #创建定时任务，每5秒通知前端更新页面状态
        # add_job(websocketPage, 'web_socket_push_{}'.format(self.userId), 'interval', {'weeks': 0,
        #                                                                               'days': 0, 'hours': 0,
        #                                                                               'minutes': 0,
        #                                                                               'seconds': 5},
        #         [message, self.userId, ])

    async def system_message(self, event):
        message = event['message']

        await self.send(text_data=json.dumps({
            'message': message
        }))
