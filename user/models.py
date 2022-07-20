from django.contrib.auth.models import AbstractUser
from django.db import models


# Create your models here.


class BaseTable(models.Model):
    # 基础表 统一添加创建时间和更新时间字段
    class Meta:
        abstract = True  # 不会创建表
        db_table = 'BaseTable'

    created_time = models.DateTimeField('创建时间', auto_now_add=True)
    updated_time = models.DateTimeField('更新时间', auto_now=True)


class User(AbstractUser):
    # 用户表
    class Meta:
        db_table = "user"

    REQUIRED_FIELDS = []  # 让Django默认必填的邮箱变成非必填
    name = models.CharField("昵称", null=True, max_length=200, default=None)
    mail_id = models.IntegerField("钉钉映射", null=True,default=None)
    phone = models.CharField("手机号码", null=True, max_length=200, default=None)
    usericon = models.CharField("头像", null=True, max_length=200, default=None)
    drep = models.CharField("部门", null=True, max_length=200, default=None)


class Role(BaseTable):
    # 角色表
    class Meta:
        db_table = "role"

    name = models.CharField("角色名", null=False, max_length=64, default="")
    auth = models.TextField("菜单权限JSON",blank=True,null=True, default='')
    status = models.IntegerField("删除状态",blank=True,null=True, default=1)


class UserRole(BaseTable):
    # 用户角色关系表
    class Meta:
        db_table = "user_role"

    user_id = models.IntegerField("用户id", null=False, default=0)
    role_id = models.IntegerField("角色id", null=False, default=0)

class Jurisdiction(BaseTable):
    # 权限表
    class Meta:
        db_table = "Jurisdiction"

    name = models.CharField("权限名称", max_length=200,null=False, default=None)
    path = models.CharField("前端页面路径",max_length=200, null=True, default=None)
    title = models.CharField("中文名称",max_length=200, null=True, default=None)
    up_id = models.IntegerField("上级权限id", null=True, default=None)
    level = models.IntegerField("权限分级", null=True, default=None)
    status = models.IntegerField("删除状态", null=True, default=1)

class Role_Jurisdiction(BaseTable):
    # 权限-角色关系表
    class Meta:
        db_table = "Role_Jurisdiction"
    role_id = models.IntegerField("角色id", null=False, default=None)
    Jurisdiction_id = models.IntegerField("权限id", null=False, default=None)
