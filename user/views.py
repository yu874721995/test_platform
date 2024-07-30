# Create your views here.
# import json
from datetime import datetime

import jwt
import logging
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.serializers import JSONWebTokenSerializer
from rest_framework_jwt.settings import api_settings
from rest_framework_jwt.views import JSONWebTokenAPIView
from user.utils import jwt_response_payload_handler
from django.contrib.auth import authenticate
from user.errors import ErrInvalidOldPassword, ErrUserNotFound, ErrInvalidUserID
from user.models import User, Role, UserRole
from user.serializers import UserPagingSerializer, RolePagingSerializer, UserCreateSerializer, UserRoleSerializer
from nextop_tapd import models
from rest_framework.viewsets import ModelViewSet

logger = logging.getLogger(__name__)

class UserLogin(JSONWebTokenAPIView):
    # 固定写法
    serializer_class = JSONWebTokenSerializer

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")
        # from django.http import HttpResponse
        # return HttpResponse(json.dumps(
        #     {
        #         "code": 10000,
        #         "msg": "登录成功",
        #         "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoyLCJ1c2VybmFtZSI6Inl1YmVpIiwiZXhwIjoxNzA3MzAxNDEwLCJlbWFpbCI6Inl1YmVpQHlpbnRhdGVjaC5jb20iLCJvcmlnX2lhdCI6MTcwNDcwOTQxMH0.uLccGu8taW73Iap97nTC4AapfXaZmyGiJZFRJBhZ6CY",
        #         "user": {
        #             "id": 2,
        #             "username": "yubei",
        #             "roleName": "测试、管理员",
        #             "email": "yubei@yintatech.com",
        #             "name": "余孛",
        #             "usericon": "https://img1.baidu.com/it/u=1371756451,2408220877&fm=253&fmt=auto&app=138&f=JPEG?w=500&h=500",
        #             "drep": "1"
        #         }
        #     }
        # ))
        serializer = self.get_serializer(data=request.data)
        ldap_user = authenticate(username=username, password=password)
        logger.info('{}'.format(str(ldap_user)))
        if ldap_user:
            logger.info('ldap校验返回登录人员：{}'.format(ldap_user))
            # ----------------- 复用代码开始 -----------------
            if serializer.is_valid():
                user = serializer.object.get('user') or request.user
                token = serializer.object.get('token')
                ding_exists = models.mail_list.objects.filter(email=ldap_user.email) | models.mail_list.objects.filter(ding_name=ldap_user.name)
                #如果有钉钉信息，更新部门、头像、映射id
                if ding_exists:
                    mailSet = ding_exists.values()[0]
                    mail_id = mailSet['id']
                    usericon = mailSet['userIcon']
                    drep = mailSet['ding_drep']
                    phone = mailSet['ding_phone']
                    User.objects.filter(id=ldap_user.id).update(mail_id=mail_id,usericon=usericon,drep=drep,phone=phone)#每次登录更新用户信息
                if not UserRole.objects.filter(user_id=ldap_user.id).exists():
                    UserRole.objects.create(**{
                        'user_id':ldap_user.id,
                        'role_id':3
                    })
                response_data = jwt_response_payload_handler(token, user, request)
                response = Response(response_data)
                if api_settings.JWT_AUTH_COOKIE:
                    expiration = (datetime.utcnow() +
                                  api_settings.JWT_EXPIRATION_DELTA)
                    response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                        token,
                                        expires=expiration,
                                        httponly=True)
                return response
        return Response(ErrUserNotFound)

    # def loginout(self,request):
    #     token =


class UserViewSet(GenericViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserPagingSerializer
    permission_classes = [IsAdminUser]  # 管理员权限

    def list(self, request, *args, **kwargs):
        # 用户列表
        queryset = self.get_queryset()
        keyword = request.GET.get("keyword")  # 查询关键字
        if keyword:
            # 用户名或昵称 模糊匹配
            queryset = User.objects.filter(Q(username__icontains=keyword) | Q(nickname__icontains=keyword))

        # ----------------- 复用代码开始 -----------------
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        # ----------------- 复用代码结束 -----------------

    def create(self, request, *args, **kwargs):
        # 新建用户
        password = request.data.get("password")
        user = {
            "username": request.data.get("username"),
            "nickname": request.data.get("nickname"),
            "password": make_password(password) if password else make_password("qa123456")
        }
        role_names = request.data.get("roleNames")
        if "管理员" in role_names:
            user["is_staff"] = True
        else:
            user["is_staff"] = False
        user_create_serializer = UserCreateSerializer(data=user)
        user_create_serializer.is_valid(raise_exception=True)
        user_create_serializer.save()
        user_id = User.objects.get(username=user["username"]).id

        user_role = {
            "user_id": user_id,
            "role_id": ""
        }
        for role_name in role_names:
            role_id = Role.objects.get(name=role_name).id
            user_role["role_id"] = role_id
            user_role_serializer = UserRoleSerializer(data=user_role)
            user_role_serializer.is_valid(raise_exception=True)
            user_role_serializer.save()

        return Response(user_create_serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):
        # 修改用户
        user = {
            "id": kwargs["pk"],  # 路径中的参数
            "username": request.data.get("username"),
            "nickname": request.data.get("nickname"),
        }
        role_names = request.data.get("roleNames")
        if "管理员" in role_names:
            user["is_staff"] = True
        else:
            user["is_staff"] = False
        # 获取已有实例进行更新
        instance = self.get_object()
        user_serializer = self.get_serializer(instance, data=user)
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()
        user_id = User.objects.get(username=user["username"]).id

        user_role = {
            "user_id": user_id,
            "role_id": ""
        }
        db_role_ids = [obj.role_id for obj in UserRole.objects.filter(user_id=user_id)]
        db_role_names = [Role.objects.get(id=db_role_id).name for db_role_id in db_role_ids]

        # 比较新旧角色差异
        new_roles = list(set(role_names).difference(db_role_names))
        old_roles = list(set(db_role_names).difference(role_names))
        for new_role in new_roles:  # 添加新角色
            role_id = Role.objects.get(name=new_role).id
            user_role["role_id"] = role_id
            user_role_serializer = UserRoleSerializer(data=user_role)
            user_role_serializer.is_valid(raise_exception=True)
            user_role_serializer.save()
        for old_role in old_roles:  # 删除老角色
            role_id = Role.objects.get(name=old_role).id
            user_role = UserRole.objects.get(user_id=user_id, role_id=role_id)
            user_role.delete()

        return Response(user_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        # 删除用户
        try:
            user_id = kwargs["pk"]
            user = User.objects.get(id=user_id)
            user.delete()
            user_roles = UserRole.objects.filter(user_id=user_id)
            for user_role in user_roles:
                user_role.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ObjectDoesNotExist:
            return Response(ErrUserNotFound, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def user_detail(self, request, *args, **kwargs):
        # 用户信息
        try:
            user_id = kwargs["pk"]
            user = User.objects.get(id=user_id)
            user_serializer = self.get_serializer(user)
            return Response(user_serializer.data)
        except ObjectDoesNotExist:
            return Response(ErrUserNotFound, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RoleList(ModelViewSet):
    # 角色列表（非常标准的REST Framework写法）
    queryset = Role.objects.all().order_by("id")
    serializer_class = RolePagingSerializer
    permission_classes = [IsAdminUser]

    def list(self, request, *args, **kwargs):
        # 用户列表
        queryset = self.get_queryset()
        keyword = request.GET.get("keyword")  # 查询关键字
        # if keyword:
        #     # 用户名或昵称 模糊匹配
        #     queryset = User.objects.filter(Q(username__icontains=keyword) | Q(nickname__icontains=keyword))

        # ----------------- 复用代码开始 -----------------
        queryset = self.filter_queryset(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return Response(self.get_paginated_response(serializer.data))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
        # ----------------- 复用代码结束 -----------------


class SystemResetPassword(APIView):
    permission_classes = [IsAdminUser]

    def put(self, request, *args, **kwargs):
        user_id = kwargs["pk"]
        try:
            user = User.objects.get(id=user_id)
        except:
            return Response(ErrInvalidUserID, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        user.set_password("qa123456")
        user.save()
        return Response("qa123456")


@api_view(['PUT'])
def update_password(request, *args, **kwargs):
    # 更新密码
    request_jwt = request.headers.get("Authorization").replace("Bearer ", "")
    request_jwt_decoded = jwt.decode(request_jwt, verify=False, algorithms=['HS512'])
    user_id = request_jwt_decoded["user_id"]  # 从jwt中解析用户id
    user = User.objects.get(id=user_id)
    db_password_hash = user.password
    old_password = request.data.get("oldPassword")
    new_password = request.data.get("newPassword")
    if not check_password(old_password, db_password_hash):  # 旧密码不匹配
        return Response(ErrInvalidOldPassword, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    user.set_password(new_password)  # 旧密码匹配 更新密码
    user.save()
    return Response(status=status.HTTP_200_OK)
