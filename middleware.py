# coding=utf-8
import time
import requests
from django.utils.deprecation import MiddlewareMixin
import logging
import json
from django.http import HttpResponse
from user import errors
import jwt
import re
import base64

Middleware = logging.getLogger(__name__)

free_url = [
            '/api/users/login',#登录接口
            '/test-platform/tapdMsgPush',#tapd回调
            '/test-platform/tapdMsgNewPush',#tapd回调
            '/api/test_tools/bkci_Callback',#流水线回调
            '/test-platform/callback/dingding_msg',#钉钉回调
            '/api/test_plant/ExecutionForPipeline',#流水线执行测试计划
            '/api/test_plant/checkReportStatus',#流水线查询测试结果
            '/api/test_case/dingReport',#钉钉访问s3测试报告
            '/api/test_tools/ContainerListNumber',#测试工具
            '/api/test_tools/get_examine_result',#查询审核状态
            '/api/test_tools/get_servicename_list',#获取所有yt-app-version
            '/test-platform/api/test_tools/serviceMonitorWebhook',#服务监控调用webhook
            '/test-platform/api/test_tools/bkci_Callback'#兼容公网调用callback
        ]
re_free_url = []
def reForUlr(url):
    result = False
    for pattern in re_free_url:
        # 匹配以符合正则规则的url
        if re.match(pattern, url):
            result = True
    return result
class MlmLogging(MiddlewareMixin):

    def process_request(self, request):
        # Middleware.info('请求信息:{}'.format(json.dumps(request.META, indent=2)))
        # Middleware.info('请求参数:{}'.format(str(request.body, 'utf-8')))
        # Middleware.info('请求头:{}'.format(request.META.get('PATH_INFO')))
        # Middleware.info(free_url)
        if request.META.get('PATH_INFO') in free_url or reForUlr(request.META.get('PATH_INFO')):
            pass
        elif request.headers.__contains__('Authorization'):
            if request.headers['Authorization'] == None or request.headers['Authorization'] == 'null':
                return HttpResponse(
                    json.dumps(errors.ReeNotLogin, ensure_ascii=False)
                )
            token = request.headers['Authorization'].replace('Bearer ','')
            try:
                request_jwt_decoded = jwt.decode(token, verify=False, algorithms=['HS512'])
            except Exception as e:
                Middleware.error(str(e))
                return HttpResponse(
                    json.dumps(errors.ReeNotLogin, ensure_ascii=False)
                )
            nowTime = int(time.time()) / 1000
            if request_jwt_decoded['exp'] < nowTime:
                return HttpResponse(
                    json.dumps(errors.ReeLoginTimeOut, ensure_ascii=False)
                )
        else:
            return HttpResponse(
                json.dumps(errors.ReeLoginTimeOut, ensure_ascii=False)
            )

    def process_response(self, request, response):
        response['content-type'] = 'application/json;charset=utf-8'
        if response.status_code == 500:
            response = HttpResponse(
                json.dumps(errors.SERVICE_ERROR, ensure_ascii=False)
            )
        # Middleware.info(f"状态码:{response.status_code},\n"
        #                 f"返回参数:\n{str(response.content, 'utf-8')}")
        return response

    def process_exception(self, request, exception):
        if request.headers['Host'] == 'web-test-platform.sit.yintaerp.com':
            body = str(json.loads(request.body)) if request.body else {}
            r = requests.post(
                'https://oapi.dingtalk.com/robot/send?access_token=24fa3ec4c21f6128ba26bfdf19f8ce75762a1fd768728e09dc0364f721dbc0cf',
                json={
                        'msgtype': 'markdown',
                        "markdown": {
                            'title': '报错信息提醒',
                            'text': '【报错接口】：{}'.format(request.path) +
                                    '  \n' +
                                    '【请求参数】:{}'.format(body) +
                                    '  \n' +
                                    '【报错内容】:{}'.format(str(exception))
                        },
                        'at': {
                            "atMobiles": [], 'isAtAll': True
                        }
                }, headers={"Content-Type": "application/json"})
        return None

class WsTokenVerify:
    """
        websocket 使用的 token解析中间件
    """
    def __init__(self, app):
        # Store the ASGI application we were passed
        self.app = app

    async def __call__(self, scope, receive, send):

        # headers 里面是一个个的元组类似于[(b'User-Agent',b'XXXX'),(b'token',b'XXXXX'),……]
        # 从headers中取出token
        try:
            query_string = scope['query_string']
            token = query_string.decode().split('=')[1]
            jwt_dict = jwt.decode(token, verify=False, algorithms=['HS512'])
        except Exception as e:
            # 解析失败，则不做任何处理，直接交给视图函数，视图函数会尝试从scope中取出关键信息，失败则会断开websocket连接
            return await self.app(scope, receive, send)
        # 将客户端的唯一身份标识（关键信息）加入scope
        scope['user_id'] = jwt_dict['user_id']
        scope['username'] = jwt_dict['username']
        return await self.app(scope, receive, send)
