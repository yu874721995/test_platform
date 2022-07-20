# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :Roles.py
# @Time      :2022/6/15 17:31
# @Author    :Careslten

import json
import logging
from django.http import HttpResponse
from django.core.paginator import Paginator
from test_management.common import json_request, DateEncoder, jwt_token, request_verify
from user.models import Role, UserRole, Role_Jurisdiction, Jurisdiction,User
from django.db import transaction
from django.db import connection

logger = logging.getLogger(__name__)


class RolesView():

    @classmethod
    @request_verify('post', check_params={'page': int, 'limit': int})
    def lists(cls, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=20)
        querys = Role.objects.filter(status=1).values().order_by('id')
        datas = []
        for query in querys:
            query['auth'] = list(Role_Jurisdiction.objects.filter(role_id=query['id']).values())
            datas.append(query)
        p = Paginator(datas, limit)  # 实例化分页对象
        count = p.count
        logging.info('定时任务查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'data': result
        }, cls=DateEncoder))

    @classmethod
    @request_verify('post', {'name': str, 'auth':list}, {'role_id': int})
    def create(cls, request):
        name = json_request(request, 'name', str, default=None)
        auth = json_request(request, 'auth', list, default=[])
        role_id = json_request(request, 'role_id', int, default=None)
        data = {
            'name': name
        }
        if role_id:
            role_id_exist = Role.objects.filter(id=role_id,status=1).exists()
            if not role_id_exist:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '角色已被删除'
                }))
            nameExist = Role.objects.filter(name=name, status=1).exclude(id=role_id).exists()
            if nameExist:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '角色名称重复'
                }))
            with transaction.atomic():
                save_id = transaction.savepoint()
                try:
                    Role.objects.update_or_create(defaults=data, id=role_id)
                    Role_Jurisdiction.objects.filter(role_id=role_id).delete()
                    if auth and auth != []:
                        for item in auth:
                            if Jurisdiction.objects.filter(id=item).exists():
                                Role_Jurisdiction.objects.create(**{
                                    'role_id': role_id,
                                    'Jurisdiction_id': item
                                })
                            else:
                                return HttpResponse(json.dumps({
                                    'code': 10005,
                                    'msg': '权限已不存在：{}'.format(item)
                                }))
                except Exception as e:
                    logger.error('更新角色权限失败：{}'.format(str(e)))
                    transaction.savepoint_rollback(save_id)
                    return HttpResponse(json.dumps({
                        'code': 10005,
                        'msg': '操作失败'
                    }))
        else:
            nameExist = Role.objects.filter(name=name, status=1).exists()
            if nameExist:
                return HttpResponse(json.dumps({
                    'code': 10005,
                    'msg': '角色名称重复'
                }))
            with transaction.atomic():
                save_id = transaction.savepoint()
                try:
                    Role.objects.create(**data)
                    if auth and auth != []:
                        for item in auth:
                            if Jurisdiction.objects.filter(id=item).exists():
                                Role_Jurisdiction.objects.create(**{
                                    'role_id': role_id,
                                    'Jurisdiction_id': item
                                })
                            else:
                                return HttpResponse(json.dumps({
                                    'code': 10005,
                                    'msg': '权限已不存在：{}'.format(item)
                                }))
                except Exception as e:
                    logger.error('更新角色权限失败：{}'.format(str(e)))
                    transaction.savepoint_rollback(save_id)
                    return HttpResponse(json.dumps({
                        'code': 10005,
                        'msg': '操作失败'
                    }))
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    @request_verify('post', {'role_id': int})
    def delete(cls, request):
        role_id = json_request(request, 'role_id', int, default=None)
        if role_id == 1:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '管理员角色不允许删除'
            }))
        idExist = Role.objects.filter(id=role_id, status=1).exists()
        if not idExist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '角色不存在'
            }))
        Role.objects.filter(id=role_id, status=1).update(status=2)  # 软删除角色
        Role_Jurisdiction.objects.filter(role_id=role_id).delete()  # 删除角色-权限关系表中的所有记录
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    @request_verify('post', {'user_id': int, 'role_id': int})
    def bindUser(cls, request):
        role_id = json_request(request, 'role_id', int, default=None)
        user_id = json_request(request, 'user_id', int, default=None)
        idExist = Role.objects.filter(id=role_id, status=1).exists()
        if not idExist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '角色不存在'
            }))
        userExist = UserRole.objects.filter(user_id=user_id, role_id=role_id).exists()
        if userExist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '用户已绑定该角色，无需重复绑定'
            }))
        UserRole.objects.create(**{
            'user_id': user_id,
            'role_id': role_id
        })
        if role_id == 1:
            User.objects.filter(id=user_id).update(is_staff=True)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    @request_verify('post', {'user_id': int, 'role_id': int})
    def unbindUser(cls, request):
        role_id = json_request(request, 'role_id', int, default=None)
        user_id = json_request(request, 'user_id', int, default=None)
        idExist = UserRole.objects.filter(user_id=user_id, role_id=role_id).exists()
        if not idExist:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '绑定关系不存在'
            }))
        UserRole.objects.filter(role_id=role_id, user_id=user_id).delete()
        if role_id == 1:
            User.objects.filter(id=user_id).update(is_staff=False)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    @request_verify('post')
    def userAuthMenu(cls, request):
        datas = []
        jurisdictions = []
        userid = jwt_token(request)['userId']
        is_admin = User.objects.get(id=userid).is_staff
        if is_admin:
            querys = Jurisdiction.objects.filter(status=1, level=1).values('id','name','path','title').order_by('id')
            jurisdictions = [item['id'] for item in Jurisdiction.objects.filter(status=1).values('id')]
            for query in querys:
                two_datas = []
                twos = list(Jurisdiction.objects.filter(status=1, up_id=query['id']).values('id','name','path','title'))
                for two in twos:
                    three_datas = []
                    threes = list(Jurisdiction.objects.filter(status=1, up_id=two['id']).values('id','name','path','title'))
                    for three in threes:
                        fours = list(
                            Jurisdiction.objects.filter(status=1, up_id=three['id']).values('id','name','path','title'))
                        three['children'] = fours
                        three_datas.append(three)
                    two['children'] = three_datas
                    two_datas.append(two)
                query['children'] = two_datas
                datas.append(query)
            return HttpResponse(json.dumps({
                'code': 10000,
                'msg': '操作成功',
                'authMenu': datas,
                'jurisdiction_ids': jurisdictions
            },cls=DateEncoder))
        roleId_list = [item['role_id'] for item in list(UserRole.objects.filter(user_id=userid).values('role_id'))]
        if roleId_list != []:
            cursor = connection.cursor()
            cursor.execute(
                "select * from Jurisdiction where id in (select jurisdiction_id from Role_Jurisdiction where role_id in %s GROUP BY jurisdiction_id)",
                [roleId_list])
            jurisdictions = [item[0] for item in cursor.fetchall()]

            querys = Jurisdiction.objects.filter(status=1, level=1,id__in=jurisdictions).values('id','name','path','title').order_by('id')
            for query in querys:
                two_datas = []
                twos = list(Jurisdiction.objects.filter(status=1, up_id=query['id'],id__in=jurisdictions).values('id','name','path','title'))
                for two in twos:
                    three_datas = []
                    threes = list(Jurisdiction.objects.filter(status=1, up_id=two['id'],id__in=jurisdictions).values('id','name','path','title'))
                    for three in threes:
                        fours = list(Jurisdiction.objects.filter(status=1, up_id=three['id'],id__in=jurisdictions).values('id','name','path','title'))
                        three['children'] = fours
                        three_datas.append(three)
                    two['children'] = three_datas
                    two_datas.append(two)
                query['children'] = two_datas
                datas.append(query)
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功',
            'authMenu': datas,
            'jurisdiction_ids':jurisdictions
        },cls=DateEncoder))

    @classmethod
    @request_verify('post', check_params={'page': int, 'limit': int})
    def userList(cls, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=200)
        querys = User.objects.filter().values().order_by('-id')
        p = Paginator(list(querys), limit)  # 实例化分页对象
        count = p.count
        logging.info('定时任务查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'data': result
        }, cls=DateEncoder))

    @classmethod
    @request_verify('post',{"role_id":int},check_params={'page': int, 'limit': int})
    def roleUserList(cls, request):
        page = json_request(request, 'page', int, default=1)
        limit = json_request(request, 'limit', int, default=200)
        role_id = json_request(request, 'role_id', int)
        querys = UserRole.objects.filter(role_id=role_id).values().order_by('-id')
        p = Paginator(list(querys), limit)  # 实例化分页对象
        count = p.count
        logging.info('定时任务查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count,
            'code': 10000,
            'page': page,
            'data': result
        }, cls=DateEncoder))

    @classmethod
    @request_verify('post', {"role_id": int})
    def roleJurisdictionList(cls, request):
        role_id = json_request(request, 'role_id', int)
        Jurisdiction_ids = [item['Jurisdiction_id'] for item in Role_Jurisdiction.objects.filter(role_id=role_id).values()]
        #查出所有权限
        querys = Jurisdiction.objects.filter(status=1, level=1,up_id__in=Jurisdiction_ids).values().order_by('-id')
        datas = []
        for query in querys:
            two_datas = []
            twos = list(Jurisdiction.objects.filter(status=1, up_id=query['id'],up_id__in=Jurisdiction_ids).values())
            for two in twos:
                three_datas = []
                threes = list(Jurisdiction.objects.filter(status=1, up_id=two['id'],up_id__in=Jurisdiction_ids).values())
                for three in threes:
                    fours = list(Jurisdiction.objects.filter(status=1, up_id=three['id'],up_id__in=Jurisdiction_ids).values())
                    three['children'] = fours
                    three_datas.append(three)
                two['children'] = three_datas
                two_datas.append(two)
            query['children'] = two_datas
            datas.append(query)
        return HttpResponse(json.dumps({
            'code': 10000,
            'data': datas,
            'jurisdiction_ids':Jurisdiction_ids
        }, cls=DateEncoder))
