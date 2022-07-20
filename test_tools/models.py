from django.db import models
from django.utils import timezone

# Create your models here.
class Assembly_line(models.Model):
    '''
        流水线记录表
        '''

    class Meta:
        db_table = "test_Assembly_line"

    id = models.AutoField(primary_key=True, blank=False)
    Assembly_id = models.CharField(max_length=200, blank=True, null=True, default=None, unique=True,verbose_name='流水线id')
    status = models.IntegerField(blank=False, default=1, verbose_name='正常/删除')
    Assembly_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='流水线名称')
    build_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建id')
    project = models.CharField(max_length=200, blank=True, null=True, verbose_name='所属项目')
    Assembly_type = models.IntegerField(blank=False, default=1,verbose_name='流水线类型1、后端，2、前端')
    build_status = models.IntegerField(blank=False, default=1, verbose_name='最后构建状态：1-正常，2-失败，3-构建中，4-取消构建，5-待审核')
    build_task = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建任务')
    Assembly_serviceName = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建服务')
    Assembly_serverName = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建实例')
    branch = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建分支')
    git = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后仓库地址')
    build_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建人')
    buildBeginTime = models.DateTimeField(blank=True, null=True, verbose_name='最后构建开始时间')
    buildEndTime = models.DateTimeField(blank=True, null=True, verbose_name='最后构建结束时间')
    offline = models.BooleanField(default=False,blank=True, null=True, verbose_name='最后是否下线')
    mergeMaster = models.BooleanField(default=None, blank=True, null=True, verbose_name='最后是否合并master')
    logs_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后日志地址')
    popId = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后popid')
    gateway_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后网关地址')
    build_examine = models.BooleanField(blank=True, null=True, verbose_name='最后是否需要审核')
    examine_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后最后审核人')
    updateTime = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name='最后更新时间')
    commit_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建时最后一次commit_id')
    old_Assembly_serverName = models.TextField(default=None,blank=True, null=True, verbose_name='关联serverName')

# Create your models here.
class Assembly_build_detail(models.Model):
    '''
        流水线记录表
        '''

    class Meta:
        db_table = "test_Assembly_build_detail"
        unique_together = ('Assembly_id', 'build_id')

    id = models.AutoField(primary_key=True, blank=False)
    Assembly_id = models.CharField(max_length=200, blank=True, null=True, default=None,db_index=True,verbose_name='流水线记录id')
    build_status = models.IntegerField(blank=False, default=1, verbose_name='构建状态：1-正常，2-失败，3-构建中，4-取消构建，5-待审核')
    build_task = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建任务')
    Assembly_serviceName = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建服务')
    Assembly_serverName = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建实例')
    branch = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建分支')
    git = models.CharField(max_length=200, blank=True, null=True, verbose_name='仓库地址')
    build_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建人')
    buildBeginTime = models.DateTimeField(blank=True, null=True, verbose_name='构建开始时间')
    buildEndTime = models.DateTimeField(blank=True, null=True, verbose_name='构建结束时间')
    build_id = models.CharField(max_length=200, blank=True, null=True, unique=True,verbose_name='构建id')
    offline = models.BooleanField(default=False,verbose_name='是否下线')
    mergeMaster = models.BooleanField(default=None,blank=True, null=True,verbose_name='是否合并master')
    logs_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='日志地址')
    popId = models.CharField(max_length=200, blank=True, null=True, verbose_name='popid')
    gateway_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='网关地址')
    build_examine = models.BooleanField(blank=True, null=True, verbose_name='是否需要审核')
    examine_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后审核人')
    commit_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建时最后一次commit_id')

class xxjobMenu(models.Model):

    class Meta:
        db_table = "xxjob_menu"

    id = models.AutoField(primary_key=True, blank=False)
    env = models.IntegerField(blank=True, null=True,default=1, verbose_name='环境1、联调2、预发')
    group_id = models.IntegerField(blank=True, null=True,default=None, verbose_name='任务组id')
    group_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='任务组名称')
    job_id = models.IntegerField(blank=True, null=True,default=None, verbose_name='jobid')
    status = models.IntegerField(blank=False, default=1, verbose_name='1正常/2删除')
    job_status = models.IntegerField(blank=False, default=1, verbose_name='1启用/2停止')
    job_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='job名称')
    job_owner = models.CharField(max_length=200, blank=True, null=True, default=None,verbose_name='job负责人')
    job_popid_list = models.TextField(blank=True, null=True,default=None,verbose_name='job注册节点')
    job_parmes = models.TextField(blank=True, null=True,default=None,verbose_name='job预置参数')