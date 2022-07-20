import filetype
import os
from django.http import HttpResponse
from test_management import models as manageModel
from nextop_tapd import models
import ast
import json
from utils.common import DateEncoder

#tapd项目信息
tapd_project = ast.literal_eval(manageModel.system_config.objects.filter(name='Tapd_project').values()[0]['ext'])
def get_project(request):
    return HttpResponse(json.dumps({'msg':'ok','code':200,'data':tapd_project}))

def get_iteration(request):
    project_id = request.POST.get('project_id',None)
    if project_id == None or project_id == '':
        return HttpResponse(json.dumps({'msg':'缺少参数project_id','code':500}))
    querys = models.tapd_iteration_status.objects.filter(project_id=project_id).values()
    return HttpResponse(json.dumps({'msg':'ok','code':200,'data':tuple(querys)}))

def get_demand(request):
    project_id = request.POST.get('project_id',None)
    iteration_id = request.POST.get('iteration_id', None)
    if project_id == None or project_id == '':
        return HttpResponse(json.dumps({'msg':'缺少参数project_id','code':500}))
    if iteration_id == None or iteration_id == '':
        querys = models.tapd_demand_status.objects.filter(project_id=project_id).values()
    else:
        querys = models.tapd_demand_status.objects.filter(project_id=project_id,iteration_id=iteration_id).values()
    return HttpResponse(json.dumps({'msg':'ok','code':200,'data':tuple(querys)},cls=DateEncoder))

def add_chatroom_conf(request):
    project_id = request.POST.get('project_id', None)
    iteration_id = request.POST.get('iteration_id', None)
    demand_id = request.POST.get('demand_id', None)
    webhook = request.POST.get('webhook', None)
    remark = request.POST.get('remark',None)
    if project_id == None or project_id == '':
        return HttpResponse(json.dumps({'msg':'缺少参数project_id','code':500}))
    if iteration_id == None or iteration_id == '':
        return HttpResponse(json.dumps({'msg':'iteration_id必须填写','code':500}))
    if webhook == None or webhook == '':
        return HttpResponse(json.dumps({'msg':'缺少参数webhook','code':500}))
    iteration_id_exist = models.push_chatroom_config.objects.filter(iteration_id=iteration_id).exists()
    if iteration_id_exist and iteration_id != None and iteration_id != '':
        return HttpResponse(json.dumps({'msg': '该迭代对应通知已配置', 'code': 300}))
    dic = {
        'project_id':project_id,
        'iteration_id':iteration_id,
        'demand_id':demand_id,
        'webhook_url':webhook,
        'remark':remark,
        'status':'1'
    }
    models.push_chatroom_config.objects.create(**dic)
    return HttpResponse(json.dumps({'msg': '添加成功', 'code': 200}))




