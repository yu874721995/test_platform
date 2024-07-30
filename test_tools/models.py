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
    Assembly_id = models.CharField(max_length=200, blank=True, null=True, default=None, unique=True,
                                   verbose_name='流水线id')
    status = models.IntegerField(blank=False, default=1, verbose_name='正常/删除')
    Assembly_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='流水线名称')
    build_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建id')
    project = models.CharField(max_length=200, blank=True, null=True, verbose_name='所属项目')
    Assembly_type = models.IntegerField(blank=False, default=1, verbose_name='流水线类型1、后端，2、前端')
    build_status = models.IntegerField(blank=False, default=1,
                                       verbose_name='最后构建状态：1-正常，2-失败，3-构建中，4-取消构建，5-待审核')
    build_task = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建任务')
    Assembly_serviceName = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建服务')
    Assembly_serverName = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建实例')
    branch = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建分支')
    git = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后仓库地址')
    build_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建人')
    buildBeginTime = models.DateTimeField(blank=True, null=True, verbose_name='最后构建开始时间')
    buildEndTime = models.DateTimeField(blank=True, null=True, verbose_name='最后构建结束时间')
    offline = models.BooleanField(default=False, blank=True, null=True, verbose_name='最后是否下线')
    mergeMaster = models.BooleanField(default=None, blank=True, null=True, verbose_name='最后是否合并master')
    logs_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后日志地址')
    popId = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后popid')
    gateway_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后网关地址')
    build_examine = models.BooleanField(blank=True, null=True, verbose_name='最后是否需要审核')
    examine_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后最后审核人')
    updateTime = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name='最后更新时间')
    commit_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建时最后一次commit_id')
    old_Assembly_serverName = models.TextField(default=None, blank=True, null=True, verbose_name='关联serverName')


# Create your models here.
class Assembly_build_detail(models.Model):
    '''
        流水线记录表
        '''

    class Meta:
        db_table = "test_Assembly_build_detail"
        unique_together = ('Assembly_id', 'build_id')

    id = models.AutoField(primary_key=True, blank=False)
    Assembly_id = models.CharField(max_length=200, blank=True, null=True, default=None, db_index=True,
                                   verbose_name='流水线记录id')
    build_status = models.IntegerField(blank=False, default=1,
                                       verbose_name='构建状态：1-正常，2-失败，3-构建中，4-取消构建，5-待审核')
    build_task = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建任务')
    Assembly_serviceName = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建服务')
    Assembly_serverName = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建实例')
    branch = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建分支')
    git = models.CharField(max_length=200, blank=True, null=True, verbose_name='仓库地址')
    build_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建人')
    buildBeginTime = models.DateTimeField(blank=True, null=True, verbose_name='构建开始时间')
    buildEndTime = models.DateTimeField(blank=True, null=True, verbose_name='构建结束时间')
    build_id = models.CharField(max_length=200, blank=True, null=True, unique=True, verbose_name='构建id')
    offline = models.BooleanField(default=False, verbose_name='是否下线')
    mergeMaster = models.BooleanField(default=None, blank=True, null=True, verbose_name='是否合并master')
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
    env = models.IntegerField(blank=True, null=True, default=1, verbose_name='环境1、联调2、预发')
    group_id = models.IntegerField(blank=True, null=True, default=None, verbose_name='任务组id')
    group_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='任务组名称')
    job_id = models.IntegerField(blank=True, null=True, default=None, verbose_name='jobid')
    status = models.IntegerField(blank=False, default=1, verbose_name='1正常/2删除')
    job_status = models.IntegerField(blank=False, default=1, verbose_name='1启用/2停止')
    job_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='job名称')
    job_owner = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='job负责人')
    job_popid_list = models.TextField(blank=True, null=True, default=None, verbose_name='job注册节点')
    job_parmes = models.TextField(blank=True, null=True, default=None, verbose_name='job预置参数')


class DataComparison(models.Model):
    class Meta:
        db_table = "data_comparison"

    id = models.AutoField(primary_key=True, blank=False)
    name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='对比view名称')
    primary_sql = models.TextField(null=True, default=None, verbose_name='主sql')
    secondary_sql = models.TextField(null=True, default=None, verbose_name='副sql')
    associated_field = models.CharField(max_length=200, verbose_name='对比字段')
    env = models.CharField(max_length=200, default=None, verbose_name='主sql执行环境')
    secondary_env = models.CharField(max_length=200, default=None, verbose_name='副sql执行环境')
    status = models.IntegerField(blank=False, default=1, verbose_name='1正常/2删除')
    creator = models.CharField(max_length=200, verbose_name='创建人')
    create_time = models.DateTimeField(blank=True, auto_now_add=True, verbose_name='创建时间')


class DataComparisonResult(models.Model):
    class Meta:
        db_table = "data_comparison_result"

    id = models.AutoField(primary_key=True, blank=False)
    data_comparison_id = models.IntegerField(verbose_name='数据对比viewId')
    primary_sql = models.TextField(null=True, default=None, verbose_name='主sql')
    secondary_sql = models.TextField(null=True, default=None, verbose_name='副sql')
    associated_field = models.CharField(max_length=200, verbose_name='对比字段')
    env = models.IntegerField(default=None, verbose_name='主sql执行环境')
    secondary_env = models.IntegerField(default=None, verbose_name='副sql执行环境')
    status = models.IntegerField(blank=False, default=1, verbose_name='执行状态：1-执行中，2-执行成功，3-执行失败')
    result = models.TextField(null=True, default=None, verbose_name='执行结果')
    error_content = models.TextField(null=True, default=None, verbose_name='执行报错时的错误信息')
    creator = models.CharField(max_length=200, verbose_name='执行人')
    create_time = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name='执行时间')


class JenKinsAssembly_line(models.Model):
    '''
        流水线记录表
        '''

    class Meta:
        db_table = "jenkins_test_Assembly_line"

    id = models.AutoField(primary_key=True, blank=False)
    Assembly_id = models.CharField(max_length=200, blank=True, null=True, default=None, unique=True,
                                   verbose_name='流水线id')
    status = models.IntegerField(blank=False, default=1, verbose_name='1正常/2删除')
    Assembly_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='流水线名称')
    build_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建id')
    project = models.CharField(max_length=200, blank=True, null=True, verbose_name='所属项目')
    Assembly_type = models.IntegerField(blank=False, default=1, verbose_name='流水线类型1、后端，2、前端')
    build_status = models.IntegerField(blank=False, default=1,
                                       verbose_name='最后构建状态：1-正常，2-失败，3-构建中，4-取消构建，5-待审核')
    build_task = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建任务')
    Assembly_serviceName = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建服务')
    Assembly_serverName = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建实例')
    branch = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建分支')
    git = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后仓库地址')
    build_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建人')
    buildBeginTime = models.DateTimeField(blank=True, null=True, verbose_name='最后构建开始时间')
    buildEndTime = models.DateTimeField(blank=True, null=True, verbose_name='最后构建结束时间')
    offline = models.BooleanField(default=False, blank=True, null=True, verbose_name='最后是否下线')
    mergeMaster = models.BooleanField(default=None, blank=True, null=True, verbose_name='最后是否合并master')
    logs_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后日志地址')
    popId = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后popid')
    gateway_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后网关地址')
    build_examine = models.BooleanField(blank=True, null=True, verbose_name='最后是否需要审核')
    examine_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后最后审核人')
    updateTime = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name='最后更新时间')
    commit_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建时最后一次commit_id')
    old_Assembly_serverName = models.TextField(default=None, blank=True, null=True, verbose_name='关联serverName')
    buildParmes = models.TextField(null=True, verbose_name='构建参数')
    old_buildParmes = models.TextField(null=True, verbose_name='最近一次构建参数')
    job_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='job_name')
    jacoco_build_parmes = models.JSONField(null=True,default=None,verbose_name='jacoco上一次构建参数')
    build_swatch = models.IntegerField(blank=False, default=0,
                                       verbose_name='0-关闭，1-开启')

# Create your models here.
class JenKinsAssembly_build_detail(models.Model):
    '''
        流水线记录表
        '''

    class Meta:
        db_table = "jenkins_test_Assembly_build_detail"
        unique_together = ('Assembly_id', 'build_id')

    id = models.AutoField(primary_key=True, blank=False)
    Assembly_id = models.CharField(max_length=200, blank=True, null=True, default=None, db_index=True,
                                   verbose_name='流水线记录id')  #
    build_status = models.IntegerField(blank=False, default=1,
                                       verbose_name='构建状态：1-正常，2-失败，3-构建中，4-取消构建，5-待审核')  #
    build_task = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建任务')  #
    Assembly_serviceName = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建服务')  #
    Assembly_serverName = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建实例')  #
    project = models.CharField(max_length=200, blank=True, null=True, verbose_name='所属项目')
    branch = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建分支')  #
    git = models.CharField(max_length=200, blank=True, null=True, verbose_name='仓库地址')
    build_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后构建人')
    buildBeginTime = models.DateTimeField(blank=True, null=True, verbose_name='构建开始时间')
    buildEndTime = models.DateTimeField(blank=True, null=True, verbose_name='构建结束时间')
    build_id = models.CharField(max_length=200, blank=True, null=True, unique=True, verbose_name='构建id')
    offline = models.BooleanField(default=False, verbose_name='是否下线')
    mergeMaster = models.BooleanField(default=None, blank=True, null=True, verbose_name='是否合并master')
    logs_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='日志地址')
    popId = models.CharField(max_length=200, blank=True, null=True, verbose_name='popid')
    gateway_addr = models.CharField(max_length=200, blank=True, null=True, verbose_name='网关地址')
    build_examine = models.BooleanField(blank=True, null=True, verbose_name='是否需要审核')
    examine_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='最后审核人')
    commit_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建时最后一次commit_id')
    buildParmes = models.TextField(null=True, verbose_name='构建参数')
    commits_list = models.TextField(blank=True, null=True, default=None, verbose_name='构建分支对比mastercommits')
    commits_list_4_hours = models.TextField(blank=True, null=True, default=None, verbose_name='构建前4小时内commits')
    build_reason = models.TextField(blank=True, null=True, default=None, verbose_name='构建原因')
    job_name = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='job_name')
    uat_case_run = models.IntegerField(blank=False, default=0,
                                       verbose_name='uat构建后执行测试计划，是否执行过 0-未执行 1-执行过')  #


class JenKinsExamine(models.Model):
    class Meta:
        db_table = "jenkins_examine_detail"

    id = models.AutoField(primary_key=True, blank=False)
    Assembly_id = models.CharField(max_length=200, blank=True, null=True, default=None, db_index=True,
                                   verbose_name='流水线记录id')  #
    build_id = models.CharField(max_length=200, blank=True, null=True, unique=True, verbose_name='构建id')
    examine_status = models.IntegerField(blank=False, default=1, verbose_name='构建状态：1-待审核，2-已审核，3-已取消')  #
    buildBeginTime = models.DateTimeField(blank=True, null=True, verbose_name='构建开始时间')
    examine_begin_time = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name='发起审核时间')
    examine_time = models.DateTimeField(blank=True, null=True, verbose_name='审核时间')
    examine_result = models.IntegerField(blank=True, null=True, verbose_name='构建状态：1-通过，2-驳回')  #
    examine_man = models.CharField(max_length=200, blank=True, null=True, verbose_name='审核人')
    commit_id = models.CharField(max_length=200, blank=True, null=True, verbose_name='构建时最后一次commit_id')


class sqlTreasureBox(models.Model):
    class Meta:
        db_table = "sqlTreasureBox"

    id = models.AutoField(primary_key=True, blank=False)
    status = models.IntegerField(blank=True, null=True, default=0, db_index=True, verbose_name='删除状态1、正常、1-删除')
    project_id = models.IntegerField(blank=True, null=True, default=None, db_index=True, verbose_name='文件id')  #
    database_config_id = models.IntegerField(blank=True, null=True, default=None, db_index=True, verbose_name='数据id')  #
    creator = models.CharField(max_length=200, blank=True, null=True, default=None, db_index=True, verbose_name='创建人')  #
    name = models.CharField(max_length=200, blank=True, null=True, default=None, db_index=True, verbose_name='名称')  #
    value = models.TextField(verbose_name='SQL内容')
    update_time = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name='修改时间')
    create_time = models.DateTimeField(blank=True, null=True, auto_now_add=True,verbose_name='创建时间')

class MockApiModel(models.Model):

    class Meta:
        db_table = "test_mock_api_main"

    id = models.AutoField(primary_key=True, blank=False)
    status = models.IntegerField(blank=True, null=True, default=1, verbose_name='删除状态1、启用、0-禁用')
    project_id = models.IntegerField(blank=True, null=True, default=None, verbose_name='所属项目')
    server_name = models.CharField(max_length=200, blank=True, null=True, default=None,
                                   verbose_name='所属服务')
    name = models.CharField(max_length=200, blank=True, null=True, default=None,db_index=True,
                            verbose_name='mock接口名称')
    is_delete = models.IntegerField(blank=True, null=True, default=0,
                                    verbose_name='删除状态0-正常，1-删除')
    creator = models.CharField(max_length=200, blank=True, null=True, default=None,
                            verbose_name='操作人')
    update_time = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name='修改时间')
    create_time = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name='创建时间')
class MockApiVersionModel(models.Model):

    class Meta:
        db_table = "test_mock_api_version"
    id = models.AutoField(primary_key=True, blank=False)
    parent_id = models.IntegerField(verbose_name='mock接口id')
    status = models.IntegerField(blank=True, null=True, default=1, db_index=True, verbose_name='删除状态1、启用、0-禁用')
    version_name = models.CharField(max_length=200, blank=True, null=True, default=None,
                               verbose_name='版本名称')
    version = models.CharField(max_length=200, blank=True, null=True, default=None,
                               verbose_name='mock接口版本')
    method = models.CharField(max_length=200, blank=True, null=True, default=None,
                               verbose_name='请求方式')
    url = models.CharField(max_length=200, blank=True, null=True, default=None,
                               verbose_name='请求url')
    headers_data = models.TextField(verbose_name='请求内容')
    request_data = models.TextField(verbose_name='请求内容')
    response_data = models.TextField(verbose_name='返回参数')
    is_delete = models.IntegerField(blank=True, null=True, default=0, verbose_name='删除状态0-正常，1-删除')
    creator = models.CharField(max_length=200, blank=True, null=True, default=None,
                               verbose_name='操作人')
    update_time = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name='修改时间')
    create_time = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name='创建时间')

class Jacoco_build_history(models.Model):
    class Meta:
        db_table = "jacoco_build_history"

    id = models.AutoField(primary_key=True, blank=False)
    job_name = models.CharField(max_length=200, null=False)
    server_name = models.CharField(max_length=200,null=False)
    service_name = models.CharField(max_length=200, null=False)
    task_id = models.CharField(max_length=200,null=False)
    status = models.IntegerField(blank=True, null=True, default=1, verbose_name='删除状态1、执行中、2-成功、3-失败')
    error_msg = models.TextField()
    jacoco_report = models.CharField(max_length=200,null=False)
    creator = models.CharField(max_length=200,null=False)
    update_time = models.DateTimeField(blank=True, null=True, auto_now=True, verbose_name='修改时间')
    create_time = models.DateTimeField(blank=True, null=True, auto_now_add=True, verbose_name='创建时间')

class monitorWebhookHistory(models.Model):
    class Meta:
        db_table = "monitor_webhook_history"

    id = models.AutoField(primary_key=True, blank=False)
    status = models.CharField(max_length=200,  verbose_name='警告类型')
    alertname = models.CharField(max_length=200,verbose_name='alter名称')
    deployment = models.CharField(max_length=200, verbose_name='告警服务')
    namespace = models.CharField(max_length=200,verbose_name='命名空间')
    severity = models.CharField(max_length=200, verbose_name='kube')
    description = models.TextField(verbose_name='告警内容')
    startsAt = models.CharField(max_length=200, verbose_name='推送中的服务startime')
    endsAt = models.CharField(max_length=200,verbose_name='推送中的服务endtime')
    fingerprint = models.CharField(max_length=200, verbose_name='标识')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    content_text = models.TextField(verbose_name='原始报文')
