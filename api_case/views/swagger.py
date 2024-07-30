# coding=utf-8
import re, time, os
from threading import Thread
import yaml
from requests import get
from django.db.models import Q
from rest_framework import status as status_code
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import api_view
from utils.pagination import CustomPagination
from utils.api_response import MyResponse, MyThread
from api_case.models import SwaggerApi
from api_case.serializers import SwaggerSerializer
import test_management.models as model
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import as_completed
from test_case.models import Case


class SwaggerViewSet(ModelViewSet):
    queryset = SwaggerApi.objects.all()
    serializer_class = SwaggerSerializer

    def list(self, request, *args, **kwargs):
        # 使用线程预处理有用例的接口
        def have_case():
            query_2 = SwaggerApi.objects.filter(~Q(case_status=2))
            swagger_id = []
            for obj in query_2:
                case = Case.objects.filter(only_api=obj.only_api)
                if case:
                    swagger_id.append(obj.id)
            SwaggerApi.objects.filter(id__in=swagger_id).update(case_status=2)
            # print("查找完成: ", swagger_id)
        # todo 存在 模块重复bug 暂不使用
        # 使用线程预处理有用例的接口
        # def get_module():
        #     query_serve = SwaggerApi.objects.values_list("module").distinct()
        #     query_module = moduleMent.objects.filter(type=1).values("name", "server_env")
        #     for ser in query_serve:
        #         for mod in query_module:
        #             if ser[0] in mod['server_env']:
        #                 # print(mod['server_env'], "1212", ser[0], mod['name'])
        #                 SwaggerApi.objects.filter(module=ser[0]).update(module=mod['name'])
        #                 continue
        #     # print("查找完成: ", swagger_id)
        # Thread(target=get_module, args=()).start()

        url_all = request.META.get("QUERY_STRING")
        if "status=all" not in url_all:  # 不是有用例页面时才调用此方法
            t = Thread(target=have_case, args=())
            t.start()
        query = Q()
        status = request.GET.get('status')
        if status == "all":  # 不包括新增与待更新
            query &= ~Q(status='新增') & ~Q(status="待更新")
        if status == "new_update":  #
            query &= Q(status='新增') | Q(status="待更新")
        if status == "待更新":
            query &= Q(status="待更新")
        if status == "新增":
            query &= Q(status="新增")
        if status == "有用例":
            query &= Q(status="有用例")
        if status == "废弃":
            query &= Q(status="废弃")
        method = request.GET.get("method")
        if method:  # 如果传了请求方法
            query &= Q(method__icontains=method)
        name = request.GET.get("name")
        if name:  # 如果传了用例名称
            query &= Q(api_name__icontains=name)
        url = request.GET.get('url')
        if url:
            query &= Q(url__icontains=url)
        module = request.GET.get('module')
        if module:
            query &= Q(module__icontains=module)
        queryset = SwaggerApi.objects.filter(query).order_by('-id')  # 按照用例api_name正序
        cp = CustomPagination()
        page = cp.paginate_queryset(queryset, request=request)
        size = cp.get_page_size(request)
        if page is not None:
            serializer = SwaggerSerializer(page, many=True)
            data = cp.get_paginated_response(serializer.data)
            data.update({'size': size})
            return Response(data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        request.data.update({'only_api': request.data['method'] + request.data['url']})
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return MyResponse(serializer.data)


def re_pattern(content, pattern=r'[^\*" /:?\\|<>]'):
    text = re.findall(pattern, content, re.S)
    content = "".join(text)
    return content


def get_gateway_yaml():
    route_dict = {}
    with open(os.path.dirname(__file__) + '/nextop-gateway.yaml') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        gateway_data = data['spring']['cloud']['gateway']['routes']
        for route in gateway_data:
            service_name = route['uri'].split('//')[-1]
            gateway_path = route['predicates'][0].split('=/')[-1].split('/')[0]
            route_dict.update({service_name: gateway_path})
    return route_dict


@api_view(['POST'])
def sync_swagger(request):
    # gateway_path = get_gateway_yaml()
    # url_list_all = get('http://10.0.1.149:8888/getJson').json()['data']  # 运维给的数据链接接口
    # # url_list_all = ["http://10.0.1.149/nextop-finance/full.api.json","http://10.0.1.149/nextop-finance-receivable/full.api.json",]  # 调试使用
    # print(f"【开始同步数据, swagger url数量: {len(url_list_all)}】\n")
    start_time = time.time()
    sync_data = dict()
    results = []
    thread_pool = ThreadPoolExecutor()
    # for url in url_list_all:
    #     # aa = AnalysisSwaggerJson(url, gateway_path)
    #     # aa.analysis_json_data()
    #     args = (AnalysisSwaggerJson(url, gateway_path).analysis_json_data,)
    #     results.append(thread_pool.submit(*args))
    # for res in as_completed(results):
    print("总耗时", time.time() - start_time)
    url_dict=eval(model.system_config.objects.get(name='swagger_urls').ext)
    for url in url_dict:
        args = (AnalysisSwaggerJsonNew(url_dict[url]).analysis_json_data,)
        results.append(thread_pool.submit(*args))
    for res in as_completed(results):
        result = res.result()
        if result:
           sync_data.update(result)

    return Response(data={"code": 10000, "msg": "同步接口信息成功", "data": sync_data},
                     status=status_code.HTTP_200_OK)

class AnalysisSwaggerJsonNew(object):
    def __init__(self, url):
        self.url = url
        self.definitions = None
        self.sync_result = {}  # 存储同步、新增、更新的结果数据

    def analysis_json_data(self):
            module = self.url.split('/')[-3]  # 链接内获得模块
            try:
                url_data = get(self.url).json()  # 获取最新的swagger数据
                if not url_data:
                    # print(f"{self.url} 无数据！")
                    return
                # if module in ("nextop-mail", "nextop-oms", "nextop-mail-center-main"):
                # print(f"{self.url} 可能重复，暂不做处理")
                # return
            except Exception as e:
                print(f"接口地址{self.url}获取数据失败: {e}")
                self.sync_result['url访问异常'] = self.url
                return self.sync_result
            api_data = url_data['paths']  # 获取url的接口数据
            self.definitions = url_data['definitions']  # 获取url的对象数据
            # 查询数据库是否存在该模块， 且获得一个 接口唯一的 列表
            query_module = SwaggerApi.objects.filter(module=module).values("only_api")
            if query_module:
                api_update_num = 0
                new_api = []  # 存储新增\更新的接口列表
                # print(f"数据库的{module} 已有接口数:", len(query_module))
                for path, path_v in api_data.items():  # 第1层循环获取 swagger的接口url信息
                    for g_method, g_method_v in path_v.items():  # 第2层循环获取 swagger的接口 请求方法、参数信息
                        if g_method in('post','get','delete','put'):
                            api_name = g_method_v.get("tags")[0]  # 获得接口标签说明
                            api = self.wash_params(module, g_method_v, path, g_method, api_name)
                            only_api = {'only_api': api['only_api']}
                            if only_api in query_module:
                                # 查询到 用例only_api = 与原接口的only_api的那一条数据进行对比
                                query = SwaggerApi.objects.filter(
                                    only_api=api["only_api"], module=module).order_by('updated_time').last()
                                # 如果不是全部相等，则有改动，写入新数据，同时更新接口状态
                                # print(query.params, api["params"])
                                if not all((query.api_name == api['api_name'],
                                            query.module == api['module'],
                                            query.method == api["method"],
                                            query.url == api["url"],
                                            str(query.params) == str(api["params"]),
                                            str(query.only_api) == str(api["only_api"])
                                            )):
                                    SwaggerApi.objects.filter(
                                        id=query.id).update(api_name=api["api_name"],
                                                            module=api["module"],
                                                            method=api["method"], url=api["url"],
                                                            params=api["params"],
                                                            responses=api["responses"],
                                                            assert_res=api["assert_res"],
                                                            only_api=api["only_api"],
                                                            status=2, )
                                    api_update_num += 1
                                    self.sync_result[
                                        f'  接口变更 {api["only_api"]}'] = f"{module} 有改动"
                            else:
                                # print("不存在，则直接添加到数据库更新列表, 状态为新增")
                                new_api.append(
                                    SwaggerApi(api_name=api["api_name"], module=api["module"],
                                               method=api["method"], url=api["url"],
                                               params=api["params"], responses=api["responses"],
                                               assert_res=api["assert_res"],
                                               only_api=api["only_api"], status=1
                                               ))
                                self.sync_result[f'  新增{api["only_api"]}'] = f"{module} 新增接口"
                                api_update_num += 1
                # 统一把新增接口写入 到数据库
                if new_api:
                    SwaggerApi.objects.bulk_create(new_api)
                    self.sync_result[f'{module}服务更新接口数'] = api_update_num
                else:
                    if not api_update_num:
                        self.sync_result[f'服务 {module}'] = "无新增"
                # print(f"{module} if耗时", time.time() - start_times1)
            else:  # 不存在该模块，全量存储到数据库， 状态新增
                database_list = []  # 数据库列表放该模块的所有用例
                for path, path_v in api_data.items():  # 第一层k是path, 如/bom，v值是各种请求方法, 如method
                    # 第二层k=req_method, v是接口详情，name=tags+description
                    for method, method_v in path_v.items():
                        if method in('post','get','delete','put'):
                            api_name = method_v.get("tags")[0]  # 获得接口标签说明
                            api = self.wash_params(module, method_v, path, method, api_name)
                            database_list.append(
                                SwaggerApi(api_name=api["api_name"], module=api["module"],
                                           method=api["method"], url=api["url"],
                                           params=api["params"], responses=api["responses"],
                                           assert_res=api["assert_res"],
                                           only_api=api["method"] + api["url"], status=1
                                           ))
                self.sync_result[f"{module}"] = f"数据库无该服务数据，新增总共 {len(database_list)}个接口"
                SwaggerApi.objects.bulk_create(database_list)
                print(f"{module} 服务新增接口数：{len(database_list)}，已存储到数据库")
            return self.sync_result

    def wash_params(self, module, params, path, method, tag):
            api_dict = {"api_name": "", "module": '', "method": "", "url": "",
                        "params": {}, "responses": {}, "assert_res": {}, "only_api": ""}
            case_name = params['summary']  # .replace('/', '_').replace(" ", "_").replace(":", "_")
            case_name = re_pattern(case_name)
            api_dict['api_name'] = f'{tag}_{case_name}'
            api_dict['module'] = module
            api_dict['method'] = method.upper()
            api_dict['url'] = '/' + module +path.replace('{', '$').replace('}', '')
            api_dict['only_api'] = api_dict['method'] + api_dict['url']
            parameters = params.get('parameters', {})  # 请求参数是列表存储，不存在则改成空字典
            responses = params.get('responses', {})  # 字典格式

            for attr in parameters:
                if attr.get('in') == 'body':  # attr是字典，body和query不会同时出现
                    schema = attr.get('schema')
                    required = "必传参数" if attr.get("required") else "非必传"
                    if schema and '$ref' in schema:
                        param_body = self.get_ref(schema)
                        if param_body:
                            for param_k, param_v in param_body.items():
                                if 'example' in param_v.keys():
                                    api_dict['params'].update({param_k: f"举例_{param_v['example']}"})
                                else:
                                    api_dict['params'].update(
                                        {param_k: f"{param_v.get('type')}_{param_v.get('description')}"})
                                    # 传参里面又带对象
                                    if param_v.get('items') and '$ref' in param_v.get('items'):
                                        i_param = self.get_ref(param_v.get('items')) or {
                                            "传参对象items$ref没参数": {"description": "没有数据"}}
                                        param_v_dict = {}
                                        for i_k, i_v in i_param.items():
                                            param_v_dict.update({i_k: i_v.get('description')})
                                        api_dict['params'].update({param_k: param_v_dict})
                        else:
                            api_dict['params'].update({
                                attr.get('name'): f"{attr.get('description')}({required})"})
                    elif schema and 'items' in schema:
                        if "$ref" in schema['items']:
                            param_body = self.get_ref(schema['items']) or {
                                "schema$items$ref": {"description": "没数据"}}
                            if param_body:
                                for param_k, param_v in param_body.items():
                                    if 'example' in param_v.keys():
                                        api_dict['params'].update({param_k: f"举例_{param_v['example']}"})
                                    else:
                                        api_dict['params'].update(
                                            {param_k: f"{param_v.get('type')}_{param_v.get('description')}"})
                                        # 传参里面又带对象
                                        if param_v.get('items') and '$ref' in param_v.get('items'):
                                            i_param = self.get_ref(param_v.get('items'))
                                            param_v_dict = {}
                                            for i_k, i_v in i_param.items():
                                                param_v_dict.update({i_k: i_v.get('description')})
                                            api_dict['params'].update({param_k: param_v_dict})
                        else:
                            api_dict['params'].update(
                                {attr.get('name'): f"{attr.get('description')}({required})"})

                    else:
                        api_dict['params'].update(
                            {attr.get('name'): f"{attr['in']}_{attr.get('description')}({required})"})
                elif attr.get('in') == 'query':
                    name = attr.get('name')
                    if 'example' not in attr.keys():
                        required = "必传参数" if attr.get("required") else "非必传"
                        api_dict['params'].update(
                            {name: f"{attr.get('type')}_{attr.get('description')}({required})"})
                    else:
                        api_dict['params'].update({name: f"举例_{attr.get('example')}"})
                else:
                    name = attr.get('name') or "没有name"
                    if 'example' not in attr.keys():
                        required = "必传参数" if attr.get("required") else "非必传"
                        api_dict['params'].update(
                            {'传参IN类型': attr.get("in"),
                             'schema$ref': attr.get("schema"),
                             'items$ref': attr.get("items"),
                             name: f"{attr.get('type')}_{attr.get('description')}({required})"})
                    else:
                        api_dict['params'].update({name: f"举例_{attr.get('example')}"})
            if '200' in responses:  # 只获取 code码 200下的数据
                res = responses['200']
                if res.get('schema') and '$ref' in res.get('schema'):  # 第一层schema对象
                    response_param = self.get_ref(res.get('schema')) or {"schema$ref没参数": {"description": "没有数据"}}
                    for k, attr_v in response_param.items():
                        if 'example' not in attr_v.keys():
                            api_dict['responses'].update({k: attr_v.get('description')})
                            if attr_v.get('items') and '$ref' in attr_v.get('items'):  # 第二层items对象
                                attr_v_dict = {}
                                attr_v_items = attr_v.get('items')
                                items2_param = self.get_ref(attr_v_items) or {"第2层items$ref没参数": {"description": "没数据"}}
                                for items_k, items_v in items2_param.items():
                                    attr_v_dict.update({items_k: items_v.get('description')})
                                api_dict['responses'].update({k: attr_v_dict})
                            api_dict['assert_res'] = {'schema有$ref': 200}
                        else:
                            api_dict['responses'].update({'eq': attr_v.get('example')})
                elif res.get('schema') and 'items' in res.get('schema'):  # schema下是item对象时
                    if "$ref" in res.get('schema')['items']:
                        # print(res.get('schema')['items'])
                        items1_param = self.get_ref(res.get('schema')['items'])
                        if items1_param:
                            for items1_k, items1_v in items1_param.items():
                                api_dict['responses'].update({items1_k: items1_v.get('description')})
                                if items1_v.get('items') and '$ref' in items1_v.get('items'):  # 第二层items对象
                                    items1_v_dict = {}
                                    items1_param = self.get_ref(items1_v.get('items')) or {
                                        "第二层items$ref没参数": {"description": "没有数据"}}
                                    for items_k, items_v in items1_param.items():
                                        items1_v_dict.update({items_k: items_v.get('description')})
                                    api_dict['responses'].update({items1_k: items1_v_dict})
                            api_dict['assert_res'] = {'items有$ref': 200}
                        else:
                            api_dict['responses'].update({"schema['items']": res.get('schema')['items']})

                    else:
                        api_dict['assert_res'] = {'items没有$ref': 200}
                else:  # 返回参数里面没有object对象的情况
                    api_dict['responses'].update({'默认返回参数': responses['200']['description']})
                    api_dict['assert_res'] = {'status_code': 200}
            else:
                print("不是200的情况", responses.items())
            return api_dict

    def get_ref(self, ref_dict):
            ref = ref_dict.get('$ref')
            if ref:
                ref_name = ref_dict.get('$ref').split('/')[-1]
                param_key = re.findall(r'[^«»]+', ref_name)[-1]
                # param_key = re.findall(r'[^«»]+', ref_dict.get('originalRef'))[-1]
                key_in = self.definitions.get(param_key)
                if key_in and key_in.get('properties'):
                    response_param = key_in['properties'] if key_in else {}
                    return response_param  # 返回 properties 数据


#以前的方法，和赢他的swagger不兼容，暂未使用
class AnalysisSwaggerJson(object):
    def __init__(self, url, path):
        self.url = url
        self.definitions = None
        self.sync_result = {}  # 存储同步、新增、更新的结果数据
        self.path = path  # 服务名对应的gateway， 访问

    def analysis_json_data(self):
        module = self.url.split('/')[-2]  # 链接内获得模块
        gateway = module
        for serve_name in self.path.keys():
            if serve_name in module:  # gateway配置解析出来的key 名与 swagger 的模块名匹配
                gateway = self.path[serve_name]
        # print("对比：", gateway, "----", module)
        try:
            url_data = get(self.url).json()  # 获取最新的swagger数据
            if not url_data:
                # print(f"{self.url} 无数据！")
                return
            # if module in ("nextop-mail", "nextop-oms", "nextop-mail-center-main"):
                # print(f"{self.url} 可能重复，暂不做处理")
                # return
        except Exception as e:
            print(f"接口地址{self.url}获取数据失败: {e}")
            self.sync_result['url访问异常'] = self.url
            return self.sync_result
        api_data = url_data['paths']  # 获取url的接口数据
        self.definitions = url_data['definitions']  # 获取url的对象数据
        # 查询数据库是否存在该模块， 且获得一个 接口唯一的 列表
        query_module = SwaggerApi.objects.filter(module=module).values("only_api")
        if query_module:
            api_update_num = 0
            new_api = []  # 存储新增\更新的接口列表
            # print(f"数据库的{module} 已有接口数:", len(query_module))
            for path, path_v in api_data.items():  # 第1层循环获取 swagger的接口url信息
                for g_method, g_method_v in path_v.items():  # 第2层循环获取 swagger的接口 请求方法、参数信息
                    api_name = g_method_v.get("tags")[0]  # 获得接口标签说明
                    api = self.wash_params(module, g_method_v, path, g_method, api_name, gateway)
                    only_api = {'only_api': api['only_api']}
                    if only_api in query_module:
                        # 查询到 用例only_api = 与原接口的only_api的那一条数据进行对比
                        query = SwaggerApi.objects.filter(
                            only_api=api["only_api"], module=module).order_by('updated_time').last()
                        # 如果不是全部相等，则有改动，写入新数据，同时更新接口状态
                        # print(query.params, api["params"])
                        if not all((query.api_name == api['api_name'],
                                    query.module == api['module'],
                                    query.method == api["method"],
                                    query.url == api["url"],
                                    str(query.params) == str(api["params"]),
                                    str(query.only_api) == str(api["only_api"])
                                    )):
                            SwaggerApi.objects.filter(
                                id=query.id).update(api_name=api["api_name"],
                                                    module=api["module"],
                                                    method=api["method"], url=api["url"],
                                                    params=api["params"],
                                                    responses=api["responses"],
                                                    assert_res=api["assert_res"],
                                                    only_api=api["only_api"],
                                                    status="待更新", )
                            api_update_num += 1
                            self.sync_result[
                                f'  接口变更 {api["only_api"]}'] = f"{module} 有改动"
                    else:
                        # print("不存在，则直接添加到数据库更新列表, 状态为新增")
                        new_api.append(
                            SwaggerApi(api_name=api["api_name"], module=api["module"],
                                       method=api["method"], url=api["url"],
                                       params=api["params"], responses=api["responses"],
                                       assert_res=api["assert_res"],
                                       only_api=api["only_api"], status="新增"
                                       ))
                        self.sync_result[f'  新增{api["only_api"]}'] = f"{module} 新增接口"
                        api_update_num += 1
            # 统一把新增接口写入 到数据库
            if new_api:
                SwaggerApi.objects.bulk_create(new_api)
                self.sync_result[f'{module}服务更新接口数'] = api_update_num
            else:
                if not api_update_num:
                    self.sync_result[f'服务 {module}'] = "无新增"
            # print(f"{module} if耗时", time.time() - start_times1)
        else:  # 不存在该模块，全量存储到数据库， 状态新增
            database_list = []  # 数据库列表放该模块的所有用例
            for path, path_v in api_data.items():  # 第一层k是path, 如/bom，v值是各种请求方法, 如method
                # 第二层k=req_method, v是接口详情，name=tags+description
                for method, method_v in path_v.items():
                    api_name = method_v.get("tags")[0]  # 获得接口标签说明
                    api = self.wash_params(module, method_v, path, method, api_name, gateway)
                    database_list.append(
                        SwaggerApi(api_name=api["api_name"], module=api["module"],
                                   method=api["method"], url=api["url"],
                                   params=api["params"], responses=api["responses"],
                                   assert_res=api["assert_res"],
                                   only_api=api["method"] + api["url"], status="新增"
                                   ))
            self.sync_result[f"{module}"] = f"数据库无该服务数据，新增总共 {len(database_list)}个接口"
            SwaggerApi.objects.bulk_create(database_list)
            print(f"{module} 服务新增接口数：{len(database_list)}，已存储到数据库")
        return self.sync_result

    def wash_params(self, module, params, path, method, tag, gateway):
        api_dict = {"api_name": "", "module": '', "method": "", "url": "",
                    "params": {}, "responses": {}, "assert_res": {}, "only_api": ""}
        case_name = params['summary']  # .replace('/', '_').replace(" ", "_").replace(":", "_")
        case_name = re_pattern(case_name)
        api_dict['api_name'] = f'{tag}_{case_name}'
        api_dict['module'] = module
        api_dict['method'] = method.upper()
        api_dict['url'] = '/' + gateway + path.replace('{', '$').replace('}', '')
        api_dict['only_api'] = api_dict['method'] + api_dict['url']
        parameters = params.get('parameters', {})  # 请求参数是列表存储，不存在则改成空字典
        responses = params.get('responses', {})  # 字典格式

        for attr in parameters:
            if attr.get('in') == 'body':  # attr是字典，body和query不会同时出现
                schema = attr.get('schema')
                required = "必传参数" if attr.get("required") else "非必传"
                if schema and '$ref' in schema:
                    param_body = self.get_ref(schema)
                    if param_body:
                        for param_k, param_v in param_body.items():
                            if 'example' in param_v.keys():
                                api_dict['params'].update({param_k: f"举例_{param_v['example']}"})
                            else:
                                api_dict['params'].update(
                                    {param_k: f"{param_v.get('type')}_{param_v.get('description')}"})
                                # 传参里面又带对象
                                if param_v.get('items') and '$ref' in param_v.get('items'):
                                    i_param = self.get_ref(param_v.get('items')) or {
                                        "传参对象items$ref没参数": {"description": "没有数据"}}
                                    param_v_dict = {}
                                    for i_k, i_v in i_param.items():
                                        param_v_dict.update({i_k: i_v.get('description')})
                                    api_dict['params'].update({param_k: param_v_dict})
                    else:
                        api_dict['params'].update({
                            attr.get('name'): f"{attr.get('description')}({required})"})
                elif schema and 'items' in schema:
                    if "$ref" in schema['items']:
                        param_body = self.get_ref(schema['items']) or {
                            "schema$items$ref": {"description": "没数据"}}
                        if param_body:
                            for param_k, param_v in param_body.items():
                                if 'example' in param_v.keys():
                                    api_dict['params'].update({param_k: f"举例_{param_v['example']}"})
                                else:
                                    api_dict['params'].update(
                                        {param_k: f"{param_v.get('type')}_{param_v.get('description')}"})
                                    # 传参里面又带对象
                                    if param_v.get('items') and '$ref' in param_v.get('items'):
                                        i_param = self.get_ref(param_v.get('items'))
                                        param_v_dict = {}
                                        for i_k, i_v in i_param.items():
                                            param_v_dict.update({i_k: i_v.get('description')})
                                        api_dict['params'].update({param_k: param_v_dict})
                    else:
                        api_dict['params'].update(
                            {attr.get('name'): f"{attr.get('description')}({required})"})

                else:
                    api_dict['params'].update(
                        {attr.get('name'): f"{attr['in']}_{attr.get('description')}({required})"})
            elif attr.get('in') == 'query':
                name = attr.get('name')
                if 'example' not in attr.keys():
                    required = "必传参数" if attr.get("required") else "非必传"
                    api_dict['params'].update(
                        {name: f"{attr.get('type')}_{attr.get('description')}({required})"})
                else:
                    api_dict['params'].update({name: f"举例_{attr.get('example')}"})
            else:
                name = attr.get('name') or "没有name"
                if 'example' not in attr.keys():
                    required = "必传参数" if attr.get("required") else "非必传"
                    api_dict['params'].update(
                        {'传参IN类型': attr.get("in"),
                         'schema$ref': attr.get("schema"),
                         'items$ref': attr.get("items"),
                         name: f"{attr.get('type')}_{attr.get('description')}({required})"})
                else:
                    api_dict['params'].update({name: f"举例_{attr.get('example')}"})
        if '200' in responses:  # 只获取 code码 200下的数据
            res = responses['200']
            if res.get('schema') and '$ref' in res.get('schema'):  # 第一层schema对象
                response_param = self.get_ref(res.get('schema')) or {"schema$ref没参数": {"description": "没有数据"}}
                for k, attr_v in response_param.items():
                    if 'example' not in attr_v.keys():
                        api_dict['responses'].update({k: attr_v.get('description')})
                        if attr_v.get('items') and '$ref' in attr_v.get('items'):  # 第二层items对象
                            attr_v_dict = {}
                            attr_v_items = attr_v.get('items')
                            items2_param = self.get_ref(attr_v_items) or {"第2层items$ref没参数": {"description": "没数据"}}
                            for items_k, items_v in items2_param.items():
                                attr_v_dict.update({items_k: items_v.get('description')})
                            api_dict['responses'].update({k: attr_v_dict})
                        api_dict['assert_res'] = {'schema有$ref': 200}
                    else:
                        api_dict['responses'].update({'eq': attr_v.get('example')})
            elif res.get('schema') and 'items' in res.get('schema'):  # schema下是item对象时
                if "$ref" in res.get('schema')['items']:
                    # print(res.get('schema')['items'])
                    items1_param = self.get_ref(res.get('schema')['items'])
                    if items1_param:
                        for items1_k, items1_v in items1_param.items():
                            api_dict['responses'].update({items1_k: items1_v.get('description')})
                            if items1_v.get('items') and '$ref' in items1_v.get('items'):  # 第二层items对象
                                items1_v_dict = {}
                                items1_param = self.get_ref(items1_v.get('items')) or {
                                    "第二层items$ref没参数": {"description": "没有数据"}}
                                for items_k, items_v in items1_param.items():
                                    items1_v_dict.update({items_k: items_v.get('description')})
                                api_dict['responses'].update({items1_k: items1_v_dict})
                        api_dict['assert_res'] = {'items有$ref': 200}
                    else:
                        api_dict['responses'].update({"schema['items']": res.get('schema')['items']})

                else:
                    api_dict['assert_res'] = {'items没有$ref': 200}
            else:  # 返回参数里面没有object对象的情况
                api_dict['responses'].update({'默认返回参数': responses['200']['description']})
                api_dict['assert_res'] = {'status_code': 200}
        else:
            print("不是200的情况", responses.items())
        return api_dict

    def get_ref(self, ref_dict):
        ref = ref_dict.get('$ref')
        if ref:
            ref_name = ref_dict.get('$ref').split('/')[-1]
            param_key = re.findall(r'[^«»]+', ref_name)[-1]
            # param_key = re.findall(r'[^«»]+', ref_dict.get('originalRef'))[-1]
            key_in = self.definitions.get(param_key)
            if key_in and key_in.get('properties'):
                response_param = key_in['properties'] if key_in else {}
                return response_param  # 返回 properties 数据
