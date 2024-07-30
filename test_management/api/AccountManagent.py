# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten

import base64
import json
import logging
import time
import requests
import os
import easyocr
from test_management import models
from django.http import HttpResponse
from django.db import transaction
from test_management.common import json_request,request_verify
from django.core.paginator import Paginator
from test_management.common import DateEncoder,jwt_token
from django.db.models import Q
from nextop_tapd import models as tapd_models

r = requests.session()
logger = logging.getLogger(__name__)


class AccountSetView():

    @classmethod
    @request_verify('post',{'account':int,'project_id':int,'password':str,'env':str})
    def checkAccount(cls,request):
        return HttpResponse(json.dumps({
            'code': 10005,
            'msg': '该功能暂时不可用'
        }))
        project_id = json_request(request, 'project_id', int)
        account = json_request(request, 'account', int)
        password = json_request(request, 'password')
        env = json_request(request, 'env')
        r.headers = {
            'canary': env,
            'x-ca-reqid': return_times(),
            'x-ca-reqtime': return_time(),
            'origin': 'https://saas.nextop.com',
            'referer': 'https://saas.nextop.com/'
        }
        captchaImg = \
            r.get('https://api.nextop.com/auth/login/img?{}'.format(return_time())).json()['data'].split('base64,')[1]
        try:
            with open('cap.png', 'wb') as f:
                f.write(base64.b64decode(captchaImg))
                f.close()
                reader = easyocr.Reader(['ch_sim', 'en'])
                result = reader.readtext('cap.png')
                captcha = result[0][1]
                os.remove('cap.png')
        except Exception as e:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '验证码识别失败，请重试'
            }))

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
        else:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '添加失败,未获取到cookie，请检查账号密码并重试'
            }))
        r.cookies.clear()  # 清除实例的旧cookie
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功',
            'cookie':cookie,
            'data':tenantList
        }))

    @classmethod
    @request_verify('post',
        {'project_id':int,
        'account': int,
        'password': str,
        'account_name': str,
        'env': str}
    )
    def create(cls, request):
        project_id = json_request(request, 'project_id', int)
        account = json_request(request, 'account', int)
        password = json_request(request, 'password')
        cookie = json_request(request, 'cookie',default=None)
        account_name = json_request(request, 'account_name')
        tenantList = json_request(request, 'tenant',list)
        env = json_request(request, 'env')
        creator = jwt_token(request)['username']
        tenantId = json_request(request, 'tenantId',default=None)
        if not tenantList:
            r.headers = {
                'canary': env,
                'x-ca-reqid': return_times(),
                'x-ca-reqtime': return_time(),
                'origin': 'https://saas.nextop.com',
                'referer': 'https://saas.nextop.com/'
            }
            captchaImg = \
                r.get('https://api.nextop.com/auth/login/img?{}'.format(return_time())).json()['data'].split('base64,')[
                    1]

            try:
                with open('cap.png', 'wb') as f:
                    f.write(base64.b64decode(captchaImg))
                    f.close()
                    reader = easyocr.Reader(['ch_sim', 'en'])
                    result = reader.readtext('cap.png')
                    captcha = result[0][1]
                    os.remove('cap.png')
            except Exception as e:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '验证码识别失败，请重试'
                }))
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
                tenantList = r.get('https://api.nextop.com/user/user/tenant/dropdown?sysIdentification=1').json()[
                    'data']
            else:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '添加失败,未获取到cookie，请检查账号密码并重试'
                }))
            r.cookies.clear()  # 清除实例的旧cookie
        if not tenantId:
            tenantId = tenantList[0]['tenantId']
        with transaction.atomic():
            try:

                models.ErpAccount.objects.create(
                    **{
                        'project_id': project_id,
                        'account': account,
                        'account_name':account_name,
                        'password': password,
                        'cookie': cookie,
                        'env': env,
                        'tenant':tenantList,
                        'tenantId':tenantId,
                        'creator': creator
                    }
                )
            except Exception as e:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '数据库报错{}'.format(str(e))
                }))
        r.cookies.clear()  # 清除实例的旧cookie
        r.headers = {
            'canary': env,
            'x-ca-reqid': return_times(),
            'x-ca-reqtime': return_time(),
            'origin': 'https://admin.nextop.com',
            'referer': 'https://admin.nextop.com/erp/userwhite/index',
            'authorization': eval(models.system_config.objects.get(name='admin_token').ext)[env]
        }
        add_white = r.post('https://admin.nextop.com/sys/erpUser/updateConcurrentUser',
                           json={"userAccount": account, "concurrentLogin": 1}).json()
        if add_white['code'] != '000000' and add_white['code'] != 'B00010':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '添加白名单失败，请更新admin后台token配置'
            }))
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '添加成功'
        }))

    @classmethod
    def pagelist(cls, request):
        page = json_request(request, 'page', int,default=1)
        limit = json_request(request, 'limit', int,default=20)
        project_id = json_request(request,'project_id',int,not_null=False,default=None)
        account_name = json_request(request, 'account_name', int, not_null=False, default=None)
        env = json_request(request, 'env', not_null=False,default=None)
        account = json_request(request, 'account', not_null=False,default=None)
        creator = json_request(request, 'creator', not_null=False,default=None)
        query = Q(is_del=1)
        if project_id:
            query &= Q(project_id=project_id)
        if env:
            query &= Q(env=env)
        if account:
            query &= Q(account__contains=account)
        if creator:
            query &= Q(creator__contains=creator)
        if account_name:
            query &= Q(account_name__contains=account_name)
        querys = models.ErpAccount.objects.filter(query).values()
        datas = []
        for query in querys:
            query['tenant'] = eval(query['tenant']) if query['tenant'] and query['tenant'] != '' else None
            datas.append(query)
        p = Paginator(datas, limit)
        count = p.count
        logging.info('账号查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count, 'page': page, 'code': 10000, 'items': result
        },cls=DateEncoder))

    @classmethod
    def delete(cls, request):
        id = json_request(request, 'id', int)
        exist = models.ErpAccount.objects.filter(id=id, is_del=1).exists()
        if not exist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '不存在或已删除'
            }))
        with transaction.atomic():
            models.ErpAccount.objects.filter(id=id, is_del=1).update(is_del=2)
            return HttpResponse(json.dumps({
                'code': 10000,
                'msg': '操作成功'
            }))

    @classmethod
    @request_verify('post',
        {'id': int,
        'project_id':int,
        'account': int,
        'password': str,
        'cookie': str,
        'account_name': str,
        'env': str},
    )
    def update(cls,request):
        id = json_request(request,'id',int)
        project_id = json_request(request, 'project_id', int)
        account = json_request(request, 'account', int)
        password = json_request(request, 'password')
        cookie = json_request(request, 'cookie')
        account_name = json_request(request, 'account_name')
        tenantList = json_request(request, 'tenant', list,default=None)
        env = json_request(request, 'env')
        creator = jwt_token(request)['username']
        tenantId = json_request(request, 'tenantId', default=None)
        if not tenantList:
            r.headers = {
                'canary': env,
                'x-ca-reqid': return_times(),
                'x-ca-reqtime': return_time(),
                'origin': 'https://saas.nextop.com',
                'referer': 'https://saas.nextop.com/'
            }
            captchaImg = \
                r.get('https://api.nextop.com/auth/login/img?{}'.format(return_time())).json()['data'].split('base64,')[
                    1]

            try:
                with open('cap.png', 'wb') as f:
                    f.write(base64.b64decode(captchaImg))
                    f.close()
                    reader = easyocr.Reader(['ch_sim', 'en'])
                    result = reader.readtext('cap.png')
                    captcha = result[0][1]
                    os.remove('cap.png')
            except Exception as e:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '验证码识别失败，请重试'
                }))
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
                tenantList = r.get('https://api.nextop.com/user/user/tenant/dropdown?sysIdentification=1').json()[
                    'data']
            else:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '添加失败,未获取到cookie，请检查账号密码并重试'
                }))
            r.cookies.clear()  # 清除实例的旧cookie
        if not tenantId:
            tenantId = tenantList[0]['tenantId']
        IdExists = models.ErpAccount.objects.filter(id=id,is_del=1).exists()
        if not IdExists:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '记录不存在或已删除'
            }))
        with transaction.atomic():
            try:
                models.ErpAccount.objects.update_or_create(
                    defaults={
                        'project_id': project_id,
                        'account': account,
                        'password': password,
                        'cookie': cookie,
                        'account_name':account_name,
                        'env': env,
                        'tenantId':tenantId,
                        'tenant':tenantList,
                        'creator': creator
                    },id=id,is_del=1)
            except Exception as e:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '数据库报错{}'.format(str(e))
                }))
        r.cookies.clear()  # 清除实例的旧cookie
        r.headers = {
            'canary': env,
            'x-ca-reqid': return_times(),
            'x-ca-reqtime': return_time(),
            'origin': 'https://admin.nextop.com',
            'referer': 'https://admin.nextop.com/erp/userwhite/index',
            'authorization': eval(models.system_config.objects.get(name='admin_token').ext)[env]
        }
        add_white = r.post('https://admin.nextop.com/sys/erpUser/updateConcurrentUser',
                           json={"userAccount": account, "concurrentLogin": 1}).json()
        if add_white['code'] != '000000' and add_white['code'] != 'B00010':
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '添加白名单失败，请更新admin后台token配置'
            }))
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '修改成功'
        }))

    @classmethod
    def mail_list(cls,request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=1000)
        query = Q(ding_status='是')
        querys = tapd_models.mail_list.objects.filter(query).values('id','ding_name')
        p = Paginator(tuple(querys), limit)
        count = p.count
        logging.info('查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count, 'page': page, 'code': 10000, 'items': result
        }, cls=DateEncoder))

def return_times():
    times = str(int(time.time() * 1000)) + '.0125'
    return times


def return_time():
    times = str(int(time.time() * 1000))
    return times

