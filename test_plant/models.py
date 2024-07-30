from django.db import models
from django.utils import timezone

class ScheduledTask(models.Model):
    '''
    定时任务预录表
    '''

    class Meta:
        db_table = "test_scheduled_task"

    id = models.AutoField(primary_key=True,blank=False)
    status = models.IntegerField(blank=False,default=1, verbose_name='启用状态')
    task_name = models.CharField(max_length=200,blank=True,null=True,verbose_name='任务名称')
    func_name = models.CharField(max_length=200,blank=True,null=True,verbose_name='执行函数')

class ScheduledTaskExcu(models.Model):
    '''
    定时任务构建表
    '''

    class Meta:
        db_table = "test_scheduled_task_excu"

    id = models.AutoField(primary_key=True,blank=False)
    status = models.IntegerField(blank=False,default=1, verbose_name='启用/禁用状态')
    task_name = models.CharField(max_length=200,blank=True,null=True,verbose_name='任务名称')
    func_name = models.CharField(max_length=200,blank=True,null=True,verbose_name='执行函数')
    regjob_id = models.IntegerField(blank=True,default=None, verbose_name='执行函数id')
    task_id = models.CharField(max_length=200,blank=False,null=False,verbose_name='全局任务id')
    task_type = models.CharField(max_length=200,blank=False,null=False,verbose_name='执行策略-定时/轮训/单次')
    times = models.TextField(verbose_name='时间策略')
    start_time = models.CharField(max_length=200,default=None,blank=True,null=True,verbose_name='执行策略-定时/轮训/单次')
    end_time = models.CharField(max_length=200,default=None,blank=True,null=True,verbose_name='执行策略-定时/轮训/单次')
    args = models.TextField(blank=True,null=True,verbose_name='执行参数')
    creator = models.CharField(max_length=200,blank=False,null=False,verbose_name='定时任务构建人')
    create_time = models.DateTimeField(blank=True, null=True, verbose_name='构建时间')
    remark = models.CharField(max_length=200,default=None,blank=True,null=True,verbose_name='备注信息')
    is_del = models.IntegerField(blank=False,default=1, verbose_name='是否删除1-正常2-删除' )

class ScheduledExecution(models.Model):
    '''
    定时任务运行记录表
    '''

    class Meta:
        db_table = "test_scheduled_execution"

    id = models.AutoField(primary_key=True,blank=False)
    job_id = models.CharField(max_length=200,blank=True,null=True,verbose_name='job_id')
    status = models.CharField(max_length=200,blank=True,null=True,verbose_name='执行状态 1-成功、2-失败')
    run_time = models.DateTimeField(blank=True, null=True, verbose_name='构建时间')
    exception = models.CharField(max_length=200,blank=True,null=True,verbose_name='执行失败原因')
    duration = models.DecimalField(blank=True,null=True,max_digits=15, decimal_places=2,verbose_name='执行用时')
    finished = models.DecimalField(blank=True,null=True,max_digits=15, decimal_places=2,verbose_name='finished')
    traceback = models.TextField(blank=True,null=True,default=None,verbose_name='报错详情')
    type = models.IntegerField(blank=False,default=1, verbose_name='执行类型 1 /自动触发 2/ 手动执行 3/蓝盾触发' )




class TestPlantTask(models.Model):
    '''
    测试任务表
    '''

    class Meta:
        db_table = "test_plant"

    id = models.AutoField(primary_key=True,blank=False)
    status = models.IntegerField(blank=False,default=1, verbose_name='启用状态')
    task_name = models.CharField(max_length=200,blank=True,null=True,verbose_name='任务名称')
    task_id = models.CharField(max_length=200,blank=True,null=True, default=None,verbose_name='任务id')
    create_time = models.DateTimeField(auto_now=True,verbose_name='创建时间')
    creator = models.CharField(max_length=200, blank=True, null=True, verbose_name='创建人')
    case_list = models.TextField(blank=True,null=True,verbose_name='用例json列表')
    group_list = models.TextField(default='',blank=True, null=True, verbose_name='组合json列表')
    project_id = models.IntegerField(default=None,blank=True, null=True, verbose_name='项目id')
    env = models.CharField(max_length=200, default=None,blank=True, null=True, verbose_name='环境标签')
    account_id = models.IntegerField(default=None,blank=True, null=True, verbose_name='账号id')
    account = models.CharField(max_length=200,default=None, blank=True, null=True, verbose_name='执行账号')
    cookie = models.CharField(max_length=200,default=None, blank=True, null=True, verbose_name='cookie')
    exec_type = models.CharField(max_length=200,blank=False,default=1, verbose_name='执行策略')
    exec_time = models.TextField(blank=False,default=None, verbose_name='执行时间')
    dingding = models.CharField(max_length=200,blank=False,default=None,verbose_name='钉钉通知人')
    Last_status = models.IntegerField(blank=True,default=4, verbose_name='最后一次执行状态，1-正常，2-错误，3-执行中，4-未开始')
    is_del = models.IntegerField(blank=True,default=1, verbose_name='是否删除，1-正常，2-删除')
    service_name = models.CharField(max_length=200,blank=False,default=1, verbose_name='所属服务名称')

class TestPlantExcu(models.Model):
    '''
        测试任务执行记录表
        '''

    class Meta:
        db_table = "test_plant_excu"

    id = models.AutoField(primary_key=True, blank=False)
    plant_id = models.IntegerField(blank=False, default=1, verbose_name='计划id')
    status = models.IntegerField(blank=False, default=1, verbose_name='执行状态：1-正在执行 2-正常 5-任务异常')
    task_id = models.CharField(max_length=200, blank=True, null=True, default=None, verbose_name='任务id')
    create_time = models.DateTimeField(auto_now=True, verbose_name='执行时间')
    creator = models.CharField(max_length=200, blank=True, null=True, verbose_name='执行人')
    case_list = models.TextField(verbose_name='用例列表')
    group_list = models.TextField(default='',verbose_name='组合列表')
    project_id = models.CharField(max_length=200, default=None,blank=True, null=True, verbose_name='项目id')
    env = models.CharField(max_length=200, default=None,blank=True, null=True, verbose_name='环境标签')
    account_id = models.IntegerField(blank=False, default=1, verbose_name='测试账号id')
    account = models.CharField(max_length=200, default=None,blank=True, null=True, verbose_name='执行账号')
    cookie = models.TextField(default=None,verbose_name='账号cookie')
    case_num = models.IntegerField(blank=True,null=True, verbose_name='用例条数')
    pass_num = models.IntegerField(blank=True, null=True, verbose_name='成功条数')
    lose_num = models.IntegerField(blank=True, null=True, verbose_name='失败条数')
    duration = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name='执行用时')
    report_url = models.CharField(max_length=200, blank=True, null=True, verbose_name='测试报告地址')