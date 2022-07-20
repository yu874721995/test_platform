import json
import datetime
import requests
from test_management import models
import logging
import decimal
import jwt
from django.http import HttpResponse
from functools import wraps
from user.models import Role_Jurisdiction, UserRole,User

logger = logging.getLogger(__name__)

def get_k8s_list():
    url = 'https://10.0.10.252:7443/api/v1/namespaces/'
    token = models.system_config.objects.get(name='k8s_Authorization').ext
    headers = {
        'Authorization': token
    }
    querys = requests.get(url=url, headers=headers, verify=False).json()
    return querys


class DateEncoder(json.JSONEncoder):
    '''
    返回datetime数据时格式化
    '''

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        else:
            return json.JSONEncoder.default(self, obj)

def json_request(request, parmes, type=str, not_null=True, default=None):
    '''
    json请求提取参数
    :param request: 请求上下文
    :param parmes: 提取参数名称
    :param type: 期望参数类型，默认str
    :param not_null: 是否允许为''字符串，默认允许
    :return:
    '''
    try:
        body = json.loads(request.body)
        if body.__contains__(parmes):
            if body[parmes] == '' or body[parmes] == 'null' or body[parmes] == 'None' or body[parmes] == None:
                if not not_null:
                    return default
                return ''
            if type in [dict, list, tuple]:
                if isinstance(body[parmes], type):
                    return body[parmes]
                return eval(body[parmes])
            if isinstance(body[parmes], type):
                return body[parmes]
            else:
                try:
                    return type(body[parmes])
                except Exception as e:
                    raise ValueError('{}参数转换失败:{},原因：{}'.format(parmes, body[parmes], str(e)))
        else:
            return default
    except Exception as e:
        logger.error(str(e))
        return default


def request_verify(request_method: str, need_params=None, check_params=None):
    """
        在views方法上加装饰器 例如：@request_verify('get', [{'id':int}])
        :param request_method:
        :param need_params:
        :return:
    """
    if need_params and not isinstance(need_params, dict):
        raise ValueError('need_params使用方式错误')
    if check_params and not isinstance(check_params, dict):
        raise ValueError('check_params使用方式错误')

    def decorator(func):
        @wraps(func)
        def inner(self, request, *args, **kwargs):
            method = str(request.method).lower()
            # 先判断类型，类型不符合，直接return
            if request_method and not method == request_method.lower():
                response = "method {0} not allowed for: {1}".format(request.method, request.path)
                return response_failure(response)
            request.params = {}
            if method == 'get':
                if not request.GET:
                    if need_params:
                        response = "缺少参数:{}".format(list(need_params.keys())[0])
                        return response_failure(response)
                else:
                    params = {}
                    request_params = request.GET
                    for item in request_params:
                        params.update({item: request_params.get(item)})
                    # get 必填参数校验
                    if need_params:
                        for need_param_name in need_params.keys():
                            if not params.__contains__(need_param_name):
                                response = "参数 {0} 不能为空".format(need_param_name)
                                return response_failure(response)
                            try:
                                if params[need_param_name] == None:
                                    response = "参数 {0} 不能为None".format(need_param_name)
                                    return response_failure(response)
                                need_params[need_param_name](params.get(need_param_name))
                            except:
                                response = "参数 {0} 类型不正确".format(need_param_name)
                                return response_failure(response)
                    if check_params:
                        for check_param_name in check_params.keys():
                            if not params.__contains__(check_param_name):
                                continue
                            try:
                                check_params[check_param_name](
                                    params.get(check_param_name))
                            except:
                                response = "参数 {0} 类型不正确".format(check_param_name)
                                return response_failure(response)

            else:  # method == post
                if not request.body or request.body == {}:  # 参数为空的情况下
                    if need_params:  # 验证必传
                        response = "缺失参数{}".format(list(need_params.keys())[0])
                        return response_failure(response)
                else:  # 非空的时候，尝试去获取参数
                    try:
                        real_request_params = json.loads(request.body)  # 这边要try一下，如果前端传参不是json，json.loads会异常
                    except Exception as e:
                        response = "参数格式不合法"
                        return response_failure(response)
                    # 取出来以后再去判断下必填项是否每一项都有值
                    if need_params:
                        for need_param_name in need_params.keys():
                            if not real_request_params.__contains__(need_param_name):
                                response = "参数 {0} 不能为空".format(need_param_name)
                                return response_failure(response)
                            try:
                                if real_request_params[need_param_name] == None:
                                    response = "参数 {0} 不能为None".format(need_param_name)
                                    return response_failure(response)
                                need_params[need_param_name](real_request_params.get(need_param_name))
                            except:
                                response = "参数 {0} 类型不正确".format(need_param_name)
                                return response_failure(response)
                    if check_params:
                        for check_param_name in check_params.keys():
                            if not real_request_params.__contains__(check_param_name):
                                continue
                            try:
                                check_params[check_param_name](
                                    real_request_params.get(check_param_name))
                            except:
                                response = "参数 {0} 类型不正确".format(check_param_name)
                                return response_failure(response)

            return func(self, request, *args, **kwargs)

        return inner

    return decorator


# 校验结果
def response_failure(message):
    return HttpResponse(json.dumps({
        'code': 10005,
        'msg': message
    }, ensure_ascii=False), 'application/json')


def jwt_token(request):
    request_jwt = request.headers.get("Authorization").replace('Bearer ', '')
    request_jwt_decoded = jwt.decode(request_jwt, verify=False, algorithms=['HS512'])
    userid = request_jwt_decoded["user_id"]
    username = request_jwt_decoded["username"]
    email = request_jwt_decoded["email"]
    query = User.objects.get(id=userid)
    return {'userId': userid, 'username': username, 'email': email,'query':query}


def AuthJurisdiction(jurisdictionId:int):
    if not jurisdictionId or not isinstance(jurisdictionId,int):
        raise ValueError('jurisdictionId参数不能为空且必须为int类型')
    def decorator(func):
        @wraps(func)
        def inner(self, request, *args, **kwargs):
            userId = jwt_token(request)['userId']
            is_staff = User.objects.get(id=userId).is_staff
            userRole = [item['role_id'] for item in UserRole.objects.filter(user_id=userId).values('role_id')]
            JurisdictionIdQuery = [item['Jurisdiction_id'] for item in
                                   Role_Jurisdiction.objects.filter(role_id__in=userRole).values('Jurisdiction_id')]
            if jurisdictionId not in JurisdictionIdQuery and not is_staff:
                response = "没有该接口：{}访问权限".format(str(request.META.get('PATH_INFO')))
                return response_failure(response)
            return func(self, request, *args, **kwargs)
        return inner

    return decorator

