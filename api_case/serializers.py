# coding=utf8
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
import json
from django.utils.translation import gettext_lazy as _
from api_case.create_project.sample_code import generated_code
from api_case.models import Case, CaseGroup, CaseResult, MitData, SwaggerApi, CaseTestReport
from test_management.models import projectMent
from test_tools.models import xxjobMenu


class MyJSONField(serializers.JSONField):
    default_error_messages = {'invalid': _('Value must be valid JSON.')}

    def to_representation(self, value):
        if value and isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception as e:
                # print(f"str转json异常: {e} \n {value}", )
                try:
                    value = eval(
                        value.replace('null', 'None').replace('true', 'True').replace('false', 'False'))
                    print("eval转json成功！", e)
                except Exception as e:
                    value = value
                    print("第二次报错", e)
        return value

    def to_internal_value(self, data):
        try:
            if data and isinstance(data, dict):
                data = json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError):
            self.fail('dict转json异常')
        return data


class CaseCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Case
        fields = '__all__'

    # creator_nickname = serializers.CharField(required=False)  # source="creator_nickname"
    assert_res = MyJSONField(required=False, allow_null=True)
    extract_param = MyJSONField(required=False, allow_null=True)
    single_body = MyJSONField(required=False, allow_null=True)
    group_body = MyJSONField(required=False, allow_null=True)
    module = serializers.ListField(required=False, allow_null=True)
    # use_fixture = MyJSONField(required=False, allow_null=True)  # 组合用例时需要调用
    pre_sql = MyJSONField(required=False, allow_null=True)
    end_sql = MyJSONField(required=False, allow_null=True)
    code = serializers.SerializerMethodField(required=False)
    only_api = serializers.SerializerMethodField(required=False)

    def get_code(self, obj):  # 唯一生成代码的地方，如果有bug ,不会生成code, 运行用例失败
        case_id, req_method, url, delay_time = obj.id, obj.req_method, obj.url, obj.delay_time
        single_body, pre_sql, end_sql = obj.single_body, obj.pre_sql, obj.end_sql
        assert_res, group_body, extract_param = obj.assert_res, obj.group_body, obj.extract_param
        # job_id, env, pop_id = None, job_param = None
        use_job = ''  # 获取xxl job保存
        if obj.use_job:
            xxl_obj = xxjobMenu.objects.get(id=obj.job_id)
            use_job = (xxl_obj.job_id, xxl_obj.env, obj.job_podid, obj.job_param)
        # 生成code, 先判断是否有 组合参数group_body，有的话就生成组合参数用的 group_code
        code = generated_code(case_id=case_id, req_method=req_method, url=url,
                              assert_res=assert_res, delay_time=delay_time, use_job=use_job,
                              body=single_body, pre_sql=pre_sql, end_sql=end_sql,
                              extract_param=extract_param)
        Case.objects.filter(id=case_id).update(code=code)
        if group_body:
            group_code = generated_code(case_id=case_id, req_method=req_method,
                                        url=url, assert_res=assert_res, delay_time=delay_time,
                                        body=group_body, pre_sql=pre_sql, use_job=use_job,
                                        end_sql=end_sql, extract_param=extract_param)
            Case.objects.filter(id=case_id).update(group_code=group_code)
        else:  # 没有组合参数时，把单参数变成组合参数
            Case.objects.filter(id=case_id).update(group_code=code)

    def get_only_api(self, obj):
        case_id, req_method, url, only_api = obj.id, obj.req_method, obj.url, obj.only_api
        new_only_api = obj.req_method + obj.url
        if not only_api:
            Case.objects.filter(id=case_id).update(only_api=new_only_api)


# 读取用例列表使用
class CaseListSerializer(serializers.ModelSerializer):
    tag = serializers.CharField(required=False, allow_null=True)
    assert_res = MyJSONField(required=False, allow_null=True)
    extract_param = MyJSONField(required=False, allow_null=True)
    single_body = MyJSONField(required=False, allow_null=True)
    group_body = MyJSONField(required=False, allow_null=True)
    pre_sql = MyJSONField(required=False, allow_null=True)
    end_sql = MyJSONField(required=False, allow_null=True)
    result = serializers.SerializerMethodField(required=False)
    module = serializers.SerializerMethodField(required=False)

    class Meta:
        model = Case
        fields = ["id", "creator_nickname", "project_id", "name", "req_method",
                  'module', 'url', 'single_body', 'group_body', 'assert_res', 'tag',
                  'result', 'pre_sql', 'extract_param', 'end_sql', 'delay_time',
                  'updated_time', 'created_time', 'source', 'have_bug',
                  'use_job', 'job_id', 'job_param', 'job_podid', 'assembly_id']

    def get_result(self, instance):
        case_id = instance.id
        try:
            case_result = CaseResult.objects.filter(case_id=case_id, case_type__in=[1, 11]).order_by('-run_time')
            if case_result:
                result = case_result[0].result
                return result
        except ObjectDoesNotExist:
            return ""
        return ""

    def get_module(self, obj):  # 读模块时用这个视图
        module = obj.module
        if module:
            module_list = eval(module)
            return module_list


# 读取用例组合使用
class CaseGroupListSerializer(serializers.ModelSerializer):
    caseId_list = serializers.SerializerMethodField(required=False)
    module = serializers.SerializerMethodField(required=False)
    case_data = serializers.SerializerMethodField(required=False)
    result = serializers.SerializerMethodField(required=False)

    class Meta:
        model = CaseGroup
        fields = ["id", "module", "name", "description", "caseId_list",
                  'case_data', 'module', 'project_id', 'result',
                  'creator_nickname', 'updated_nickname', 'created_time', 'updated_time']

    def get_result(self, instance):
        case_id = instance.id
        try:
            case_result = CaseResult.objects.filter(case_id=case_id, case_type__in=[2, 22]).order_by('-run_time')
            if case_result:
                result = case_result[0].result
                return result
        except ObjectDoesNotExist:
            return ""
        return ""

    def get_module(self, obj):  # 读模块时用这个视图
        module = obj.module
        if module:
            module_list = eval(module)
            return module_list

    def get_caseId_list(self, obj):  # 读取数据时用这个视图
        case_list = obj.caseId_list
        if case_list:
            case_id_list = eval(case_list)
            return case_id_list

    def get_case_data(self, obj):
        case_list = obj.caseId_list
        case_id_list = eval(case_list)
        data_l = []
        for i in case_id_list:
            try:
                case_data = Case.objects.get(id=i)
                data_l.append(case_data)
            except ObjectDoesNotExist:
                pass
        serializer = CaseListSerializer(data_l, many=True)
        return serializer.data


# 存储用例组合使用
class CaseGroupSerializer(serializers.ModelSerializer):
    module = serializers.ListField(required=False, allow_null=True)
    name = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    caseId_list = serializers.ListField(required=False)
    project_id = serializers.CharField(required=False)
    creator_nickname = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    updated_nickname = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = CaseGroup
        fields = '__all__'


class CaseResultSerializer(serializers.ModelSerializer):
    caseId = serializers.IntegerField(source="case_id")
    runEnv = serializers.CharField(source="run_env")
    runUserNickname = serializers.CharField(source="run_user_nickname")
    output = MyJSONField(required=False, allow_null=True)
    name = serializers.SerializerMethodField(required=False)

    class Meta:
        model = CaseResult
        fields = ["caseId", "name", "case_type", "result", "elapsed",
                  "output", "runEnv", "runUserNickname", "run_time"]
        # "case_type运行类型：1.单用例，2.组合用例 11.批量单用例，22.批量组合用例 3.计划单用例，4.计划组合用例"

    def get_name(self, obj):
        # print(obj.case_id)
        if obj.case_type in [1, 11, 3]:
            name = Case.objects.filter(id=obj.case_id)
            return name[0].name
        else:
            name = CaseGroup.objects.filter(id=obj.case_id)
            return name[0].name


class CaseTestReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseTestReport
        fields = '__all__'

    # 存储报告的序列化
    case_id = serializers.ListField(required=False, allow_null=True)
    case_group_id = serializers.ListField(required=False, allow_null=True)
    pass_id = serializers.ListField(required=False, allow_null=True)
    lose_id = serializers.ListField(required=False, allow_null=True)


class CaseTestReportListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CaseTestReport
        fields = '__all__'

    # 读取报告的序列化
    case_id = serializers.SerializerMethodField(required=False, allow_null=True)
    case_group_id = serializers.SerializerMethodField(required=False, allow_null=True)
    pass_id = serializers.SerializerMethodField(required=False, allow_null=True)
    lose_id = serializers.SerializerMethodField(required=False, allow_null=True)

    def get_case_id(self, obj):
        case_id_list = obj.case_id
        if case_id_list:
            case_id_list = eval(case_id_list)
            return case_id_list

    def get_case_group_id(self, obj):
        case_group_id = obj.case_group_id
        if case_group_id:
            case_group_id = eval(case_group_id)
            return case_group_id

    def get_pass_id(self, obj):
        pass_id = obj.pass_id
        if pass_id:
            pass_id = eval(pass_id)
            return pass_id

    def get_lose_id(self, obj):
        lose_id = obj.lose_id
        if lose_id:
            lose_id = eval(lose_id)
            return lose_id


class MitDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MitData
        fields = '__all__'

    single_body = MyJSONField(required=False, allow_null=True)
    assert_res = MyJSONField(required=False, allow_null=True)
    result = MyJSONField(required=False, allow_null=True)
    project_id = serializers.SerializerMethodField(required=False)
    only_api = serializers.SerializerMethodField(required=False)

    def get_project_id(self, obj):
        project = projectMent.objects.filter(host__icontains=obj.host_name)
        if project:
            return project[0].id

    def get_only_api(self, obj):
        api_name = SwaggerApi.objects.filter(only_api=obj.only_api)
        if api_name:
            name_list = []
            for query in api_name:
                name_list.append(query.api_name)
            return str(name_list)
        return "【swagger未找到此接口名】"


class SwaggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SwaggerApi
        fields = '__all__'

    params = MyJSONField(required=False)
    responses = MyJSONField(required=False)
    assert_res = MyJSONField(required=False)
    extend_case_id = serializers.SerializerMethodField(required=False)

    def get_extend_case_id(self, obj):
        case_id = Case.objects.filter(only_api=obj.only_api).values('id')
        extend_case_id = ''
        if case_id:
            for i in case_id:
                extend_case_id += str(i['id']) + '、'
            extend_case_id = extend_case_id.strip('、')
            SwaggerApi.objects.filter(
                id=obj.id).update(extend_case_id=extend_case_id)
            if obj.status not in "待更新":
                SwaggerApi.objects.filter(
                    id=obj.id).update(status="有用例")
            # print(extend_case_id, "extend_case_id extend_case_id")
            return extend_case_id
