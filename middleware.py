# coding=utf-8
import time
import requests
from django.utils.deprecation import MiddlewareMixin
import logging
import json
from django.http import HttpResponse
from user import errors
import jwt
import base64

Middleware = logging.getLogger(__name__)


class MlmLogging(MiddlewareMixin):

    def process_request(self, request):
        Middleware.info('请求信息:{}'.format(json.dumps(request.META, indent=2)))
        Middleware.info('请求参数:{}'.format(str(request.body, 'utf-8')))
        Middleware.info('请求头:{}'.format(request.headers))
        if request.META.get('PATH_INFO') in ['/api/users/login','/tapdMsgPush','/tapdMsgNewPush','/api/test_tools/bkci_Callback','/callback/dingding_msg']:
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
        Middleware.info(f"状态码:{response.status_code},\n"
                        f"返回参数:\n{str(response.content, 'utf-8')}")
        return response

    def process_exception(self, request, exception):
        if request.headers['Host'] == 'test-platform-api.nextop.com':
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
