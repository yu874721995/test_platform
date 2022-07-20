# coding=utf-8
from django.db import models


class BaseTable(models.Model):  # 公共字段
    class Meta:
        abstract = True
        db_table = 'BaseTable'
    created_time = models.DateTimeField('创建时间', auto_now_add=True)
    updated_time = models.DateTimeField('更新时间', auto_now=True)


class Case(BaseTable):
    objects = None

    class Meta:
        db_table = "case"   # 测试用例表
    name = models.CharField("用例名称", max_length=255, null=False)
    module = models.CharField("所属模块", max_length=255, null=True)
    req_method = models.CharField("请求方法get/post", max_length=100, null=False)
    url = models.CharField("请求地址", max_length=100, null=False)
    single_body = models.TextField("单接口参数", max_length=100000, null=True)
    group_body = models.TextField("多接口参数", max_length=100000, null=True)
    assert_res = models.TextField("断言", max_length=10000, null=True, blank=True,)
    tag = models.IntegerField("环境标签1联调2预发3生产", null=True, blank=True)
    extract_param = models.CharField("从结果提取参数", max_length=255, null=True, blank=True)
    code = models.TextField("单用例代码", max_length=100000, null=True)
    group_code = models.TextField("组合用例代码", max_length=100000, null=True)
    pre_sql = models.TextField("前置sql", max_length=10000, null=True)
    end_sql = models.TextField("后置sql", max_length=10000, null=True)
    project_id = models.IntegerField("项目id", null=True)
    use_fixture = models.TextField("使用的fixture", max_length=50000, null=True)
    creator_nickname = models.CharField("创建人昵称", max_length=255, null=True)
    only_api = models.CharField("接口唯一名称", max_length=255, blank=True)
    source = models.CharField("用例来源", max_length=100, null=False, default="手动创建")
    delay_time = models.IntegerField("用例执行前的延时", null=True)
    use_job = models.IntegerField("是否使用xxl 1使用0不使用", null=True)
    job_id = models.IntegerField("存储xxjob_menu库的id，获取job数据", null=True)
    job_param = models.CharField("xxl的执行参数", max_length=255, null=True)
    job_podid = models.CharField("xxl的执行服务器ip", max_length=255, null=True)
    assembly_id = models.IntegerField("流水线的id", null=True)
    have_bug = models.IntegerField("1未转bug 2已转bug", null=True, default=1)



class CaseGroup(BaseTable):
    objects = None

    class Meta:
        db_table = "case_group"  # 组合用例表

    name = models.CharField("用例名称", max_length=255, null=False)
    module = models.CharField("所属模块", max_length=255, null=True)
    description = models.CharField("组合用例描述", max_length=255, null=True)
    caseId_list = models.CharField("包含单接口用例", max_length=255, null=False)
    code = models.TextField("组合用例代码", max_length=50000, null=True)
    project_id = models.IntegerField("项目id", null=False)
    creator_nickname = models.CharField("创建人昵称", null=True, max_length=255)
    updated_nickname = models.CharField("修改人昵称", null=True, max_length=255)


class CaseResult(BaseTable):
    objects = None

    class Meta:
        db_table = "case_result"  # 测试结果表

    case_id = models.IntegerField("用例id", null=False)
    case_type = models.IntegerField(
        "运行类型：1.单用例，2.组合用例 11.批量单用例，22.批量组合用例 3.计划单用例，4.计划组合用例", null=True)
    result = models.CharField("运行结果", max_length=50, null=False)
    elapsed = models.CharField("耗时", max_length=50, null=False)
    output = models.TextField("输出日志", null=False, default="")
    run_env = models.CharField("运行环境", max_length=100, null=False)
    run_user_nickname = models.CharField("运行用户昵称", null=False, max_length=64)
    run_time = models.DateTimeField("运行时间", auto_now=True)


class CaseTestReport(BaseTable):
    objects = None

    class Meta:
        db_table = "case_test_report"  # 测试报告表

    case_id = models.TextField("用例id列表", null=True)
    case_group_id = models.TextField("组合用例id列表", null=True)
    report_name = models.CharField("报告名称", max_length=255, null=True)
    run_cookie = models.CharField("运行账号", max_length=255, null=True)
    run_env = models.CharField("运行环境", max_length=100, null=True)
    case_num = models.IntegerField("总用例数", null=True)
    pass_num = models.IntegerField("通过数量", null=True)
    lose_num = models.IntegerField("失败数量", null=True)
    pass_id = models.TextField("通过的用例id", null=True)
    lose_id = models.TextField("失败的用例id", null=True)
    result = models.CharField("运行结果Pass Fail", max_length=50, null=True)
    elapsed = models.CharField("耗时", max_length=50, null=True)
    output = models.TextField("过程输出日志", null=True, default="")
    run_user_nickname = models.CharField("运行用户昵称", null=True, max_length=64)
    report_status = models.IntegerField("报告状态：0 执行中，1 已完成", null=True)


class MitData(models.Model):
    objects = None

    class Meta:
        # managed = False
        db_table = 'mit_data'   # mitmproxy 接口抓包数据表
    id = models.AutoField(primary_key=True)
    only_api = models.CharField("接口唯一字段", max_length=200)
    module = models.CharField("接口所属服务", max_length=200, null=True)
    created_time = models.DateTimeField("创建时间", blank=True, null=True)
    req_method = models.CharField("请求方法", max_length=100)
    host_name = models.CharField("请求的服务器host名", max_length=100)
    url = models.CharField("请求地址", max_length=100)
    single_body = models.TextField("请求数据", blank=True, null=True)
    result = models.TextField("返回结果", blank=True, null=True)
    ip = models.CharField("本地host", max_length=200, default="")
    env = models.IntegerField("环境标签1联调 2预发 3生产 0未知", null=True, blank=True)
    is_bug = models.IntegerField("1没有转bug，2已转bug", null=True, blank=True, default=1)
    elapsed = models.DecimalField("接口响应时间", max_digits=10, decimal_places=3, null=True)
    assert_res = models.TextField("默认断言", max_length=1000, blank=True, null=True)
    tag = models.IntegerField("标签，默认1联调", blank=True, null=True, default=1)
    status = models.IntegerField("1没有转bug2已转bug", blank=True, null=True, default=1)
    cookie = models.CharField("请求cookie", max_length=255, null=True)
    source = models.CharField("来源，默认抓包", max_length=100, blank=True, null=True, default="抓包")

class SwaggerApi(BaseTable):
    class Meta:
        db_table = 'swagger_api' # swagger接口数据表

    objects = None
    id = models.AutoField(primary_key=True)
    api_name = models.CharField("接口名称", max_length=255)
    module = models.CharField("所属服务", max_length=255, null=True)
    method = models.CharField("请求方法", max_length=10)
    url = models.CharField("请求地址", max_length=100)
    params = models.TextField("接口传参说明", max_length=50000, blank=True, null=True)
    responses = models.TextField("返回参数说明", max_length=50000, blank=True, null=True)
    assert_res = models.TextField("默认断言", max_length=10000, blank=True, null=True)
    status = models.CharField("接口状态：有用例、新增、更新", max_length=100, blank=True)
    only_api = models.CharField("接口唯一名称", max_length=255, blank=True)
    extend_case_id = models.TextField("关联的接口id", max_length=10000, blank=True)
    source = models.CharField("来源", max_length=50, default="swagger_api")
