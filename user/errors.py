#!/usr/bin/python
# encoding=utf-8


ErrInvalidPassword = {"data": {}, "msg": "用户名密码不匹配"}
ErrUserNotFound = {'code': 10001,"msg": "账号或密码错误"}
ErrInvalidOldPassword = {"data": {}, "msg": "初始密码错误"}
ErrInvalidUserID = {"data": {}, "msg": "无效的用户ID"}
ReeLoginTimeOut = {'code': 10003, 'page': 1, 'data': {}, 'msg': '用户登录会话过期'}
ReeNotLogin = {'code': 10003, 'page': 1, 'data': {}, 'msg': '请先登录'}
SERVICE_ERROR = {'code': 10005, 'msg': '服务器异常'}
