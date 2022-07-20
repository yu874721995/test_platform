#!/usr/bin/python
# encoding=utf-8
from rest_framework import status
from rest_framework.views import exception_handler

from user.models import Role, UserRole
from user.serializers import RoleAuthSerializer
from user.serializers import UserLoginSerializer
from nextop_tapd import models


def jwt_response_payload_handler(token, user=None, request=None):
    # 自定义响应体
    # role_id = UserRole.objects.get(user_id=user.id).role_id  # 获取角色id
    userDatail = UserLoginSerializer(user).data
    if userDatail['usericon'] == None or userDatail['usericon'] == '':
        userDatail['usericon'] = 'https://img1.baidu.com/it/u=1371756451,2408220877&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=500'
    return {
        "code":10000,
        'msg':'登录成功',
        "token": token,
        "user": userDatail,
        # "auth": RoleAuthSerializer(Role.objects.get(id=role_id)).data["auth"]  # 根据角色id获取菜单
    }


def custom_exception_handler(exc, context):
    # 根据异常自定义响应体和状态码
    if hasattr(exc, "detail"):
        if exc.detail == "缺失JWT请求头":
            response = exception_handler(exc, context)
            response.data = {
                "msg": "缺失JWT请求头",
                "data": {}
            }
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return response
        if exc.detail == "Signature has expired.":
            response = exception_handler(exc, context)
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return response
    return exception_handler(exc, context)
