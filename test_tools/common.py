import requests
import base64
from test_tools import models
import time
import logging
from django.utils import timezone
from test_plant.task import scheduler
import re
import gitlab
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def reload_cookie(username='bei.yu@lumin.top', password='Yu19950122.'):
    req = requests.session()
    userAgent = "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36"
    req.headers = {
        "Referer": "http://paas.ops.nextop.cc/login/",
        "User-Agent": userAgent,
    }
    postUrl = 'http://paas.ops.nextop.cc/login/'
    s = req.get(postUrl)
    csrf_token = s.cookies['bklogin_csrftoken']
    postData = {
        "username": username,
        "password": password,
        "csrfmiddlewaretoken": csrf_token
    }
    response = req.post(postUrl, data=postData)
    bk_token = req.cookies.get('bk_token')
    if bk_token:
        return req
    else:
        raise ValueError('获取蓝盾cookie失败')


def keys(userKey):
    key = list('careslten')
    userKey = list(userKey)
    num = 0
    for i in key:
        if num != 0:
            index = (num * 2) - num
        else:
            index = num
        if i == userKey[index]:
            userKey.pop(index)
        num += 1
    text = ''
    for i in userKey:
        text = text + i
    return base64.b64decode(text).decode("utf-8")


def reload_xxjob_cookie(env='test'):
    url = 'http://xxljob-{}.nextop.cc/xxl-job-admin/login'.format(env)
    data = {
        'userName': 'admin',
        'password': 'wlbjdyWHYAVd2EBI'
    }
    r = requests.session()
    r.headers.setdefault('content-type', 'application/x-www-form-urlencoded; charset=UTF-8')
    rsp = r.post(url, data=data)
    if rsp.status_code == 200:
        if rsp.json()['code'] == 200:
            return r
        else:
            raise ImportError('获取xxjob-cookie失败')
    else:
        raise ImportError('获取xxjob-cookie失败')


def checkBuild(req, waitting_Assembly_id, want_waitting_Assembly_status, Assembly, is_checkAudit):
    '''
    :param waitting_Assembly_id:
    :param want_waitting_Assembly_status: 1、正常构建、2、待审核，3、均可
    :param Assembly:
    :return:
    '''
    num = 0
    while num < 108:  # 最多等待三十分钟
        time.sleep(10)
        waitting_Assembly_status = models.Assembly_line.objects.get(Assembly_id=waitting_Assembly_id).build_status
        waitting_Assembly_name = models.Assembly_line.objects.get(Assembly_id=Assembly['Assembly_id']).Assembly_name
        if waitting_Assembly_status == 1 and want_waitting_Assembly_status == 1:
            # 构建
            build(req, Assembly, is_checkAudit)
            break
        if waitting_Assembly_status == 5 and want_waitting_Assembly_status == 2:
            # 构建
            build(req, Assembly, is_checkAudit)
            break
        num += 1
        logger.info(
            '监听的流水线:{}构建任务状态：{}，所属id：{}'.format(waitting_Assembly_name, waitting_Assembly_status, waitting_Assembly_id))


def checkAudit(req, Assembly):
    num = 0
    while num < 108:  # 最多等待10分钟
        time.sleep(10)
        waitting_Assembly_status = models.Assembly_line.objects.get(Assembly_id=Assembly['Assembly_id']).build_status
        waitting_Assembly_name = models.Assembly_line.objects.get(Assembly_id=Assembly['Assembly_id']).Assembly_name
        if waitting_Assembly_status == 2 or waitting_Assembly_status == 4:
            logger.info(
                '监听的流水线:{}已处于失败或取消构建:状态{},或已构建完成，停止所属自动审核任务'.format(waitting_Assembly_name, waitting_Assembly_status))
            break
        if waitting_Assembly_status == 5:
            # 审核
            Audit(req, Assembly)
            break
        num += 1
        logger.info('自动审核任务监听流水线：{}，状态：{}'.format(waitting_Assembly_name, waitting_Assembly_status))


def build(req, Assembly, is_checkAudit):
    Assembly_id = Assembly['Assembly_id']
    Assembly_type = models.Assembly_line.objects.get(Assembly_id=Assembly_id).Assembly_type
    Assembly_name = models.Assembly_line.objects.get(Assembly_id=Assembly_id).Assembly_name
    build_status = models.Assembly_line.objects.get(Assembly_id=Assembly_id).build_status
    env = models.Assembly_line.objects.get(Assembly_id=Assembly_id).project
    if build_status == 3 or build_status == 5:
        raise ValueError('该流水线已处于构建中:{}'.format(Assembly_name))
    url = 'http://devops.ops.nextop.cc/ms/process/api/user/builds/{}/{}'.format(env, Assembly_id)
    if env == 'devtest':
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
            data['offline'] = False
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
            data['offline'] = False
            data['projectType'] = "web"
            data['server_env'] = Assembly['Assembly_serverName']
            data['serviceName'] = Assembly['Assembly_serviceName']
            data['test_user'] = Assembly['examine_man']
    elif env == 'pre':
        data = {
            'BK_CI_BUILD_MSG': "",
            'BK_CI_FIX_VERSION': "0",
            'BK_CI_MAJOR_VERSION': "0",
            'BK_CI_MINOR_VERSION': "0",
            'branch_list': Assembly['branch'],
            'gitAddr': Assembly['git'],
            'offline': False,
            'server_env': "nextop-pre",
            'serviceName': Assembly['Assembly_serviceName'],
            'test_user': Assembly['examine_man']
        }
    elif env == 'production':
        data = {
            'BK_CI_BUILD_MSG': "",
            'BK_CI_FIX_VERSION': "0",
            'BK_CI_MAJOR_VERSION': "0",
            'BK_CI_MINOR_VERSION': "0",
            'gitAddr': Assembly['git'],
            'mergeMaster': Assembly['mergeMaster'],
            'namespace': "nextop-prod",
            'rollback': False,
            'serviceName': Assembly['Assembly_serviceName']
        }
    else:
        raise ValueError('env参数不合法，无法判断环境')
    structureJson = req.post(url, json=data)
    if structureJson.status_code == 200:
        if is_checkAudit == True:
            scheduler.add_job(checkAudit, run_date=timezone.now(), id=Assembly['Assembly_id'] + '_audit_now',
                              args=[req, Assembly])
            logger.info('添加流水线到自动审核列表中：{}'.format(Assembly_name))
        return True

    else:
        raise ValueError('构建失败:{}'.format(Assembly_name))


def Audit(req, Assembly, examine_status='PROCESS'):
    Assembly_name = Assembly['Assembly_name']
    Assembly_id = Assembly['Assembly_id']
    build_status = models.Assembly_line.objects.get(Assembly_id=Assembly_id).build_status
    if build_status != 5:
        raise ValueError('该流水线已不处于待审核状态:{}'.format(Assembly_name))
    Assembly_type = models.Assembly_line.objects.get(Assembly_id=Assembly_id).Assembly_type
    build_id = models.Assembly_line.objects.get(Assembly_id=Assembly_id).build_id
    env = models.Assembly_line.objects.get(Assembly_id=Assembly_id).project
    if env == 'devtest':  # 联调审核
        if Assembly_type == 1:
            examine_id = 'e-8e9ee019caeb4294a10158425f4fe496'
        elif Assembly_type == 2:
            examine_id = 'e-1b68992854154ea6997440f1f6f2f78b'
        else:
            raise ValueError('流水线类型错误:{}'.format(Assembly_name))
    elif env == 'pre':  # 预发审核
        if Assembly_type == 1:
            examine_id = 'e-c480e383a0744dc5895b297f97aa71f0'
        elif Assembly_type == 2:
            examine_id = 'e-acd3fca18e6342ae89f26a5737ab3c97'
        else:
            raise ValueError('流水线类型错误:{}'.format(Assembly_name))
    elif env == 'production':  # 生产审核
        examine_id = 'e-d611d89d83bb407daa0e9a5f40f7d1c8'
    else:
        raise ValueError('缺少env字段，无法判断审核环境:{}'.format(Assembly_name))

    review = req.post(
        'http://devops.ops.nextop.cc/ms/process/api/user/builds/{}/{}/{}/{}/review/'.format(
            env, Assembly_id, build_id, examine_id), json={
            'buildId': build_id,
            'desc': '',
            'params': [],
            'pipelineId': Assembly_id,
            'projectId': env,
            'status': examine_status,  # 自动审核，一律通过
            'suggest': ''
        })
    if review.status_code == 200:
        if review.json()['status'] != 0:
            raise ValueError('调用蓝盾审核接口失败:{}'.format(Assembly_name))
        else:
            logger.info('流水线:{}审核成功'.format(Assembly_name))
            return True

    else:
        raise ValueError('调用蓝盾审核接口失败:{}'.format(Assembly_name))


class GitOperationLibraryRemote():

    def __init__(self, username: str, password: str, private_token: str):
        self.gl = self.return_gitApi_gl(username, password, private_token)

    def project(self, projectName):
        '''
        获取指定项目
        :param projectName:
        :return:项目对象
        '''
        return self.gl.projects.list(search=projectName)

    def branchs(self, project):
        '''
        获取指定项目的所有分支
        :param project:project方法获取的项目对象
        :return:branch对象列表
        '''
        return project.branches.list()

    def createBranch(self,project,branchName,ref='master'):
        '''
        创建分支，ref未指定时默认使用master
        :param project: 项目对象
        :param branchName: 创建的分支名称
        :param ref: 从某某分支创建新分支
        :return:None
        '''
        return project.branches.create({'branch': branchName, 'ref': ref})

    def commits(self,project,ref='master'):
        '''
        获取指定项目指定分支的所有提交记录
        :param project:项目对象
        :param ref: 分支
        :return:提交记录列表
        '''
        return project.commits.list(all=True,query_parameters={'ref_name':ref})

    def diff(self,project,commit):
        '''
        获取某个提交的diff记录
        :param project: 项目对象
        :param commit: 提交的short_id 或者 直接传递commit对象
        :return:提交文件对比记录
        '''
        if isinstance(commit,str):
            return project.commits.get(commit)
        else:
            return project.commits.get(commit.short_id)

    def return_gitApi_gl(self, username, password, private_token):
        '''
        返回gitlab登录后的实例
        :param username:
        :param password:
        :return: gl-gitlab实例
        '''
        url = 'https://git.nextop.cc/'
        SIGN_IN_URL = 'https://git.nextop.cc/users/sign_in'
        LOGIN_URL = 'https://git.nextop.cc/users/auth/ldapmain/callback'
        session = requests.Session()
        sign_in_page = session.get(SIGN_IN_URL).content
        for l in sign_in_page.decode().split('\\n'):
            m = re.search('name="authenticity_token" value="([^"]+)"', l)
            if m:
                break
        token = None
        if m:
            token = m.group(1)
        if not token:
            raise ValueError('Unable to find the authenticity token')
        data = {'username': username,
                'password': password,
                'authenticity_token': token}
        r = session.post(LOGIN_URL, data=data)
        gl = gitlab.Gitlab(url, api_version=4, session=session, private_token=private_token)
        try:
            gl.auth()
            return gl
        except Exception as e:
            logger.error('gitlab验证失败{}'.format(str(e)))
            raise ValueError('gitlab验证失败')

def send_group_msg(room_name, message):
    # 从Channels的外部发送消息给Channel
    """
    from assets import consumers
    consumers.send_group_msg('ITNest', {'content': '这台机器硬盘故障了', 'level': 1})
    consumers.send_group_msg('ITNest', {'content': '正在安装系统', 'level': 2})
    :param room_name:
    :param message:
    :return:
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        'notice_{}'.format(room_name),  # 构造Channels组名称
        {
            "type": "system_message",
            "message": message,
        }
    )
