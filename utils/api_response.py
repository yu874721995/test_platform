# coding=utf-8
from threading import Thread

import jwt
from rest_framework.response import Response
from rest_framework import status


class MyResponse(Response):
    def __init__(self, data=None, code=10000, msg='ok',
                 status_code=status.HTTP_200_OK, headers=None,
                 content_type="application/json", exception=False, **kwargs):
        res_data = {'code': code, 'msg': msg}
        if data:  # 如果传了返回结果，放到data里面
            # data 响应的其他内容
            # data.update(kwargs)
            res_data['data'] = data
        super().__init__(data=res_data, status=status_code, headers=headers,
                         exception=exception, content_type=content_type)


def jwt_token(request):
    request_jwt = request.headers.get("Authorization").replace('Bearer ', '')
    request_jwt_decoded = jwt.decode(request_jwt, verify=False, algorithms=['HS512'])
    userid = request_jwt_decoded["user_id"]
    username = request_jwt_decoded["username"]
    email = request_jwt_decoded["email"]
    return {'userId': userid, 'username': username, 'email': email}


class MyThread(Thread):
    def __init__(self, func, args):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        try:
            return self.result
        except Exception as e:
            print(e)
            return None
