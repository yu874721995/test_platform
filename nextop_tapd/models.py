import django.utils.timezone as timezone
from django.db import models


class tapd_demand_status(models.Model):
    '''tapd需求记录表'''
    class Meta:
        db_table = "tapd_demand"

    id = models.AutoField(primary_key=True, blank=False)
    demand_id = models.CharField(max_length=200, blank=False, default='', verbose_name='需求id', help_text='需求id')
    demand_all_id = models.CharField(max_length=200, blank=True, default='', verbose_name='详细id', help_text='详细需求id')
    demand_name = models.CharField(max_length=200, blank=False, default='', verbose_name='需求名称', help_text='需求名称')
    status = models.CharField(max_length=200, blank=False, default='', verbose_name='需求状态', help_text='需求状态')
    name = models.CharField(max_length=200, blank=False, default='', verbose_name='需求处理人', help_text='需求处理人')
    url = models.CharField(max_length=200, blank=False, default='', verbose_name='需求链接', help_text='需求链接')
    update_time = models.DateTimeField(default=timezone.now, verbose_name='更新时间', help_text='更新时间')
    beginTime = models.CharField(max_length=200, blank=False, default='', verbose_name='需求计划开始时间', help_text='需求计划开始时间')
    endTime = models.CharField(max_length=200, blank=False, default='', verbose_name='需求计划结束时间', help_text='需求计划结束时间')
    createMan = models.CharField(max_length=200, blank=False, default='', verbose_name='创建人', help_text='创建人')
    update_to_user = models.CharField(max_length=200, blank=False, default='', verbose_name='通知人', help_text='通知人')
    iteration_name = models.CharField(max_length=200, blank=False, default='', verbose_name='所属迭代', help_text='所属迭代')
    iteration_id = models.CharField(max_length=200, blank=False, null=True,default='', verbose_name='所属迭代', help_text='所属迭代')
    project_id = models.CharField(max_length=200, blank=False, default='', verbose_name='所属项目id', help_text='所属项目id')
    project_name = models.CharField(max_length=200, blank=False, default='', verbose_name='所属项目名称', help_text='所属项目名称')
    middle = models.CharField(max_length=200, blank=False, default='', verbose_name='优先级', help_text='优先级')
    is_del = models.CharField(max_length=200, blank=False, default='1', verbose_name='是否删除', help_text='是否删除/1-正常，2已删除')
    category = models.CharField(max_length=200, blank=False, default='', verbose_name='需求分类')
    plant_id = models.CharField(max_length=200, null=True, default=None, verbose_name='需求所属测试计划')

    def __str__(self):
        return self.name

    @classmethod
    def tapd_demand_create(cls, **kwargs):
        try:
            return tapd_demand_status.objects.update_or_create(defaults=kwargs, demand_id=kwargs['demand_id'])
        except Exception as e:
            raise Exception('更新或插入失败，失败原因：{}'.format(str(e)))


class tapd_bug_status(models.Model):
    '''tapd bug记录表'''
    class Meta:
        db_table = "tapd_bug"

    id = models.AutoField(primary_key=True, blank=False)
    bug_id = models.CharField(max_length=200, blank=False, default='', verbose_name='bugid', help_text='bugid')
    bug_all_id = models.CharField(max_length=200, blank=True, default='', verbose_name='bugid', help_text='bugid')
    bug_name = models.CharField(max_length=200, blank=False, default='', verbose_name='bug名称', help_text='bug名称')
    status = models.CharField(max_length=200, blank=False, default='', verbose_name='bug状态', help_text='bug状态')
    name = models.CharField(max_length=200, blank=False, default='', verbose_name='bug处理人', help_text='bug处理人')
    url = models.CharField(max_length=200, blank=False, default='', verbose_name='bug链接', help_text='bug链接')
    update_time = models.DateTimeField(default=timezone.now, verbose_name='更新时间', help_text='更新时间')
    bug_level = models.CharField(max_length=200, blank=False, default='', verbose_name='严重程度', help_text='严重程度')
    create_Time = models.CharField(max_length=200, blank=False, default='', verbose_name='bug创建时间', help_text='bug创建时间')
    ok_man = models.CharField(max_length=200, blank=False, default='', verbose_name='修复人', help_text='修复人')
    ok_Time = models.CharField(max_length=200, blank=False, default='', verbose_name='修复时间', help_text='修复时间')
    createMan = models.CharField(max_length=200, blank=False, default='', verbose_name='创建人', help_text='创建人')
    diedai = models.CharField(max_length=200, blank=False, default='', verbose_name='所属迭代', help_text='所属迭代')
    diedai_id = models.CharField(max_length=200, blank=False, default='', verbose_name='所属迭代', help_text='所属迭代')
    project_id = models.CharField(max_length=200, blank=False, default='', verbose_name='所属项目id', help_text='所属项目id')
    project_name = models.CharField(max_length=200, blank=False, default='', verbose_name='所属项目名称', help_text='所属项目名称')
    demand_id = models.CharField(max_length=200, blank=False, default='', verbose_name='所属需求id', help_text='所属需求id')
    is_del = models.CharField(max_length=200, blank=False, default='1', verbose_name='是否删除', help_text='是否删除/1-正常，2已删除')

    def __str__(self):
        return self.name

    @classmethod
    def tapd_bug_create(cls, **kwargs):
        try:
            return tapd_bug_status.objects.update_or_create(defaults=kwargs, demand_id=kwargs['bug_all_id'])
        except Exception as e:
            raise Exception('更新或插入失败，失败原因：{}'.format(str(e)))

class tapd_iteration_status(models.Model):
    '''tapd 迭代记录表'''
    class Meta:
        db_table = "tapd_iteration"

    id = models.AutoField(primary_key=True, blank=False)
    iteration_id = models.CharField(max_length=200, blank=False, default='', verbose_name='迭代id', help_text='迭代id')
    iteration_name = models.CharField(max_length=200, blank=False, default='', verbose_name='迭代名称', help_text='迭代名称')
    iteration_status = models.CharField(max_length=200, blank=False, default='', verbose_name='是否当前迭代', help_text='是否当前迭代：1/是，2/否')
    iteration_url = models.CharField(max_length=200, blank=False, default='', verbose_name='迭代链接', help_text='迭代链接')
    begin_Time = models.CharField(max_length=200, blank=False, default='', verbose_name='迭代开始时间', help_text='迭代开始时间')
    end_Time = models.CharField(max_length=200, blank=False, default='', verbose_name='迭代结束时间', help_text='迭代结束时间')
    project_id = models.CharField(max_length=200, blank=False, default='', verbose_name='所属项目id', help_text='所属项目id')
    project_name = models.CharField(max_length=200, blank=False, default='', verbose_name='所属项目名称', help_text='所属项目名称')
    is_del = models.CharField(max_length=200, blank=False, default='1', verbose_name='是否删除', help_text='是否删除/1-正常，2已删除')


    def __str__(self):
        return self.name

class tapd_testPlant(models.Model):
    '''tapd 测试计划记录表'''
    class Meta:
        db_table = "tapd_testPlant"

    id = models.AutoField(primary_key=True, blank=False)
    plant_id = models.CharField(max_length=200, blank=False, default='', verbose_name='测试计划id', help_text='测试计划id')
    plant_big_id = models.CharField(max_length=200, blank=False, default='', verbose_name='测试计划id', help_text='测试计划id')
    plant_name = models.CharField(max_length=200, blank=False, default='', verbose_name='测试计划名称', help_text='测试计划名称')
    plant_status = models.CharField(max_length=200, blank=False, default='', verbose_name='测试计划状态', help_text='测试计划状态')
    plant_man = models.CharField(max_length=200, blank=False, default='', verbose_name='测试计划负责人', help_text='测试计划负责人')
    demand_num = models.CharField(max_length=200, blank=False, default='', verbose_name='需求数量', help_text='需求数量')
    case_num = models.CharField(max_length=200, blank=False, default='', verbose_name='用例数量', help_text='用例数量')
    test_pass = models.CharField(max_length=200, blank=False, default='', verbose_name='测试通过率', help_text='测试通过率')
    test_progress = models.CharField(max_length=200, blank=False, default='', verbose_name='测试执行进度', help_text='测试执行进度')
    plant_url = models.CharField(max_length=200, blank=False, default='', verbose_name='测试计划url', help_text='测试计划url')
    plant_begin_Time = models.CharField(max_length=200, blank=False, default='', verbose_name='测试计划开始时间', help_text='测试计划开始时间')
    plant_end_Time = models.CharField(max_length=200, blank=False, default='', verbose_name='测试计划结束时间', help_text='测试计划结束时间')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='加入时间', help_text='加入时间')
    iteration_id = models.CharField(max_length=200, blank=False, default='', verbose_name='迭代id', help_text='迭代id')
    iteration_name = models.CharField(max_length=200, blank=False, default='', verbose_name='迭代名称', help_text='迭代名称')
    project_id = models.CharField(max_length=200, blank=False, default='', verbose_name='所属项目id', help_text='所属项目id')
    project_name = models.CharField(max_length=200, blank=False, default='', verbose_name='所属项目名称', help_text='所属项目名称')
    is_del = models.CharField(max_length=200, blank=False, default='1', verbose_name='是否删除', help_text='是否删除/1-正常，2已删除')
    category = models.CharField(max_length=200, blank=False, default='0', verbose_name='所属模块')


    def __str__(self):
        return self.name


class mail_list(models.Model):
    '''钉钉通讯录及tapd名称映射表'''
    class Meta:
        db_table = "mail_list"
    id = models.AutoField(primary_key=True, blank=False)
    tapd_name = models.CharField(max_length=200, blank=False, default='', verbose_name='tapd名称', help_text='tapd名称')
    ding_name = models.CharField(max_length=200, blank=False, default='',verbose_name='钉钉名称',help_text='钉钉名称')
    ding_userid = models.CharField(max_length=200, blank=False, default='',verbose_name='钉钉用户id',help_text='钉钉用户id')
    ding_phone = models.CharField(max_length=200, blank=False, default='', verbose_name='手机号', help_text='手机号')
    email = models.CharField(max_length=200, blank=False, default='', verbose_name='邮箱', help_text='邮箱')
    userIcon = models.CharField(max_length=200, blank=False, default='', verbose_name='头像', help_text='头像')
    ding_drep = models.CharField(max_length=200, blank=False, default='', verbose_name='部门', help_text='部门')
    ding_is_boss = models.CharField(max_length=200, blank=False, default='', verbose_name='是否主管', help_text='是否主管')
    ding_boss_id = models.CharField(max_length=200, blank=False, default='', verbose_name='直属主管UserID', help_text='直属主管UserID')
    ding_status = models.CharField(max_length=200, blank=False, default='', verbose_name='激活状态', help_text='激活状态')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='加入时间', help_text='加入时间')

    def __str__(self):
        return self.name


class tapd_push_record(models.Model):
    '''Tapd推送记录表'''
    class Meta:
        db_table = "push_record"
    id = models.AutoField(primary_key=True, blank=False)
    push_time = models.DateTimeField(default=timezone.now, verbose_name='推送收到时间', help_text='推送收到时间')
    push_content = models.TextField(blank=False, default='', verbose_name='推送内容', help_text='推送内容')
    send_status = models.CharField(max_length=200, blank=False, default='', verbose_name='发送状态', help_text='发送状态')
    create_man = models.CharField(max_length=200, blank=False, default='', verbose_name='触发者', help_text='触发者')
    push_man = models.CharField(max_length=200, blank=False, default='', verbose_name='推送者', help_text='推送者')
    old_status = models.CharField(max_length=200, blank=False, default='', verbose_name='旧状态', help_text='旧状态')
    new_status = models.CharField(max_length=200, blank=False, default='', verbose_name='新状态', help_text='新状态')
    type = models.CharField(max_length=200, blank=False, default='', verbose_name='类型', help_text='类型')
    is_new = models.CharField(max_length=200, blank=False, default='', verbose_name='是否新创建', help_text='是否新创建')
    ext = models.CharField(max_length=200, blank=True, default='', verbose_name='备注', help_text='备注')
    event_id = models.CharField(max_length=200, blank=True, default='', verbose_name='event_id', help_text='event_id')

    def __str__(self):
        return self.name


class push_chatroom_config(models.Model):
    '''群聊消息发送配置表'''
    class Meta:
        db_table = "push_chatroom_config"
    id = models.AutoField(primary_key=True, blank=False)
    project_id = models.CharField(max_length=200, default="",verbose_name="项目id")
    iteration_id = models.CharField(max_length=200, default="", null=True,verbose_name="迭代id")
    demand_id = models.CharField(max_length=200, default="",null=True,verbose_name="需求id")
    webhook_url = models.CharField(max_length=200, default="", verbose_name="webhook地址")
    remark = models.CharField(max_length=200, default="", null=True,verbose_name="备注信息")
    status = models.CharField(max_length=200, default="", verbose_name="启用状态")

    def __str__(self):
        return self.name

class tapd_project_conf(models.Model):
    '''tapd消息推送配置表'''
    class Meta:
        db_table = "tapd_project_conf"
    id = models.AutoField(primary_key=True, blank=False)
    status = models.IntegerField(default=1,verbose_name='是否被删除')
    iteration_id = models.CharField(max_length=200,null=True, blank=True,default=None,verbose_name="迭代id")
    tapd_project_id = models.CharField(max_length=200,verbose_name="项目id")
    demand_before_status = models.TextField(null=True, blank=True,default=None,verbose_name="需求变更初始状态")
    demand_after_status = models.TextField(null=True, blank=True,default=None, verbose_name="需求变更流转状态")
    start_time = models.DateTimeField(default=None,null=True, blank=True,verbose_name='推送生效时间', help_text='加入时间')
    end_time = models.DateTimeField(default=None,null=True, blank=True,verbose_name='推送失效时间', help_text='加入时间')
    webhook_url = models.CharField(max_length=200,null=True, blank=True,default=None,verbose_name="webhook地址")
    owner_change_push = models.CharField(max_length=200,null=True, blank=True,default='1', verbose_name='处理人变更是否通知到群，1、通知；2、不通知')
    users = models.TextField(null=True, blank=True,default=None, verbose_name='推送给XXX')
    creator = models.CharField(max_length=200, default="", verbose_name="创建人")
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')


    def __str__(self):
        return self.name

class tapd_project_middle_conf(models.Model):
    '''tapd需求滞留提醒配置表'''
    class Meta:
        db_table = "tapd_project_middle_conf"
    id = models.AutoField(primary_key=True, blank=False)
    status = models.IntegerField(default=1,verbose_name='是否被删除')
    iteration_id = models.CharField(max_length=200,null=True, blank=True,default=None,verbose_name="迭代id")
    tapd_project_id = models.CharField(max_length=200,verbose_name="项目id")
    demand_status = models.TextField(null=True, blank=True,default=None,verbose_name="监视需求状态")
    middle_status = models.TextField(null=True, blank=True, default=None, verbose_name="监视需求优先级")
    times = models.IntegerField(null=True, blank=True, default=None, verbose_name="停留时长")
    push_time = models.CharField(max_length=200,default=None,null=True, blank=True,verbose_name='推送时间')
    webhook_url = models.CharField(max_length=200,null=True, blank=True,default=None,verbose_name="webhook地址")
    users = models.TextField(null=True, blank=True,default=None, verbose_name='推送给XXX')
    creator = models.CharField(max_length=200, default="", verbose_name="创建人")
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    def __str__(self):
        return self.name

class tapd_TestCase(models.Model):
    '''tapd 测试计划记录表'''
    class Meta:
        db_table = "tapd_TestCase"

    id = models.AutoField(primary_key=True, blank=False)
    plant_big_id = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='测试计划id')
    plant_name = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='测试计划名称')
    case_id = models.CharField(max_length=200, null=True,blank=True, default=None,verbose_name='用例id')
    case_name = models.CharField(max_length=200, null=True,blank=True, default=None,verbose_name='用例名称')
    case_url = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='用例url')
    case_level = models.CharField(max_length=200, null=True,blank=True, default=None,verbose_name='用例登记')
    case_status = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='用例状态')
    case_owner = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='用例负责人')
    case_excute = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='用例执行情况')
    excute_num = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='执行次数')
    bugs = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='关联bug')
    excute_man = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='最后执行人')
    before_zhusai_Time = models.DateTimeField(default=None, null=True,blank=True,verbose_name='最后阻塞时间')
    zhusai_status = models.CharField(max_length=200, null=True,blank=True, default='0', verbose_name='迭代id', help_text='是否阻塞过 0/没有，1/有')
    zhusai_Time = models.DecimalField(max_digits=15, decimal_places=2, null=True,blank=True, default=0,verbose_name='阻塞时长')
    demand_id = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='所属需求')

class tapd_bugStatics(models.Model):
    '''tapd 测试质量统计表'''
    class Meta:
        db_table = "tapd_bugStatics"

    id = models.AutoField(primary_key=True, blank=False)
    status = models.IntegerField(null=True, blank=True, default=1, verbose_name='测试计划状态，1、开启，2、关闭')
    plant_id = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='测试计划id')
    project_id = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='项目id')
    plant_url = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='测试计划url')
    plant_name = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='测试计划名称')
    iteration_id = models.CharField(max_length=200, null=True,blank=True, default=None,verbose_name='迭代id')
    iteration_url = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='迭代url')
    iteration_name = models.CharField(max_length=200, null=True,blank=True, default=None,verbose_name='迭代名称')
    module = models.CharField(max_length=200, null=True,blank=True, default=None,verbose_name='计划所属模块')
    start_time = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='测试开始时间')
    end_time = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='测试结束时间')
    plant_time = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='剩余测试时间')
    owner = models.CharField(max_length=200, null=True,blank=True, default=None, verbose_name='测试负责人')
    case_num = models.IntegerField(null=True, blank=True, default=0, verbose_name='迭代用例总数')
    demand_num = models.IntegerField(null=True, blank=True, default=0, verbose_name='迭代需求总数')
    demand_num_url = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='需求url')
    demand_no_test_num = models.IntegerField(null=True, blank=True, default=0, verbose_name='需求未转测数量')
    demand_no_test_num_url = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='未转测需求url')
    bug_num_url = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='bugurl')
    bug_no_num_url = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='未解决url')
    bug_all_level_num_url = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='严重以上url')
    case_url = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='需求url')
    bug_num = models.IntegerField(null=True, blank=True, default=0, verbose_name='迭代bug总数')
    bug_no_num = models.IntegerField(null=True, blank=True, default=0, verbose_name='未解决bug数')
    bug_all_level_num = models.IntegerField(null=True, blank=True, default=0, verbose_name='严重及以上的数量')
    bug_all_level_num_proportion = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True, default=0, verbose_name='严重以上的占比')
    bug_rerun_count = models.IntegerField(null=True, blank=True, default=0, verbose_name='重新打开的bug数')
    bug_rerun_count_proportion = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True, default=0, verbose_name='重新打开的占比')
    test_progress = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True, default=0, verbose_name='测试执行进度')
    test_pass = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True, default=0, verbose_name='测试通过率')
    yanqi_num = models.IntegerField(null=True, blank=True, default=0, verbose_name='延期修复bug数')
    yanqi_num_proportion = models.DecimalField(max_digits=15, decimal_places=2,null=True, blank=True, default=0, verbose_name='延期修复bug占比')
    before_blockNum = models.IntegerField( null=True, blank=True, default=0, verbose_name='累计阻塞用例数')
    before_block_time = models.IntegerField(null=True, blank=True, default=0, verbose_name='阻塞时长')
    risk = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='异常信息')
    convergence_risk = models.CharField(max_length=200, null=True, blank=True, default=None, verbose_name='缺陷收敛风险')
    blockNum = models.IntegerField(null=True, blank=True, default=0, verbose_name='阻塞数')
    convergence_risk_data = models.TextField(null=True, blank=True, default=None, verbose_name='收敛详情')
    riskData = models.TextField( null=True, blank=True, default=None, verbose_name='阻塞详情')

