from django.db import models


class system_config(models.Model):
    '''系统配置信息表'''
    class Meta:
        db_table = "system_config"
    id = models.AutoField(primary_key=True, blank=False)
    name = models.CharField(max_length=200, default="", verbose_name="配置名称")
    ext = models.TextField(default="", verbose_name="配置内容")
    remark = models.CharField(max_length=200, default="", verbose_name="备注信息")
    status = models.IntegerField(default=1, verbose_name="启用状态")

    def __str__(self):
        return self.name

class ErpAccount(models.Model):
    class Meta:
        db_table = 'erp_account'

    id = models.AutoField(primary_key=True, blank=False)
    status = models.IntegerField(default=1,null=False,blank=False,verbose_name="启用状态")
    project_id = models.IntegerField(default="", verbose_name="项目id")
    account = models.TextField(default="", verbose_name="账号")
    account_name = models.CharField(max_length=200, default="", verbose_name="账号别名")
    password = models.CharField(max_length=200, default="", verbose_name="密码")
    env = models.CharField(max_length=200, default="", verbose_name="环境")
    cookie = models.TextField(verbose_name="cookie")
    tenant = models.TextField(default="",verbose_name="tenant")
    tenantId = models.CharField(default='',max_length=200,null=False,blank=False,verbose_name="绑定默认租户id")
    is_del = models.IntegerField(default=1,null=False,blank=False,verbose_name="是否删除")
    creator = models.CharField(max_length=200, default="admin", verbose_name="创建人")
    create_time = models.DateTimeField(auto_now=True,verbose_name='创建时间')


class envCommon(models.Model):
    class Meta:
        db_table = 'envCommon'

    id = models.AutoField(primary_key=True, blank=False)
    env_id = models.IntegerField(default=1,verbose_name="env_id")
    user_id = models.CharField(max_length=200,null=False,blank=False,verbose_name="user_id")
    status = models.IntegerField(default=1,verbose_name="是否删除")
    create_time = models.DateTimeField(auto_now=True,verbose_name='更新时间')

class envList(models.Model):
    class Meta:
        db_table = 'envList'

    id = models.AutoField(primary_key=True, blank=False)
    lable_name = models.CharField(max_length=200, default="", verbose_name="lable")
    env_name = models.CharField(max_length=200, default="", verbose_name="env_name")
    server_env = models.CharField(max_length=200, default="", verbose_name="server_env")
    update_time = models.DateTimeField(auto_now=True,verbose_name='更新时间')
    status = models.IntegerField(default=1,verbose_name="是否删除")

class projectMent(models.Model):
    class Meta:
        db_table = 'projectMent'
    id = models.AutoField(primary_key=True, blank=False)
    project_name = models.CharField(max_length=200, default="", verbose_name="项目名称")
    host = models.CharField(max_length=200, default="", verbose_name="项目host")
    remark = models.CharField(max_length=200, default="", verbose_name="项目描述")
    creator = models.CharField(max_length=200, default="admin", verbose_name="创建人")
    create_time = models.DateTimeField(auto_now=True, verbose_name='创建时间')

class moduleMent(models.Model):
    class Meta:
        db_table = 'moduleMent'
    id = models.AutoField(primary_key=True, blank=False)
    project_id = models.IntegerField(default=None,null=False,blank=False,verbose_name="项目id")
    name = models.CharField(max_length=200, default="", verbose_name="模块名称")
    server_env = models.CharField(max_length=200, null=True,blank=True,default="-", verbose_name="服务名")
    up_id = models.IntegerField(default=None,null=True,blank=True,verbose_name="上级id")
    type = models.IntegerField(default=1,verbose_name="模块类型1为顶级/2为二级")
    status = models.IntegerField(default=1,verbose_name="启用/禁用")
    master = models.IntegerField(default=179, verbose_name="负责人")
    dev_master = models.IntegerField(default=179, null=True,verbose_name="开发负责人")
    creator = models.CharField(max_length=200, default="admin", verbose_name="最后修改人")
    create_time = models.DateTimeField(auto_now=True, verbose_name='创建时间')

