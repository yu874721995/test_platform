import json
import logging
import requests
from test_tools import models
from django.http import HttpResponse
from test_tools.common import reload_xxjob_cookie
from test_management.common import request_verify,json_request
from django.core.paginator import Paginator
from test_management.common import DateEncoder
from django.db.models import Q

r = requests.session()
logger = logging.getLogger(__name__)

class xxjob_toolesView():

    @classmethod
    @request_verify('post',{'job_id':int,'popId':list,'env':int},{'job_parmes':str,'popId':list})
    def build_xxjob(cls,request):
        job_id = json_request(request,'job_id',int,not_null=False,default=None)
        job_parmes = json_request(request,'job_parmes',dict,not_null=False,default=None)
        env = json_request(request,'env',int,not_null=False,default=None)
        popid = json_request(request,'popId',list,not_null=False,default=None)[0]
        jobQuery = models.xxjobMenu.objects.get(job_id=job_id,env=env)
        if jobQuery.env == 1:
            r = reload_xxjob_cookie('test')
            urls = 'http://xxljob-test.nextop.cc/xxl-job-admin/jobinfo/trigger'
        else:
            r = reload_xxjob_cookie('pre')
            urls = 'http://xxljob-pre.nextop.cc/xxl-job-admin/jobinfo/trigger'
        data = {
            'id': job_id,
            'addressList': '%s' %popid
        }
        if job_parmes != None:
            data['executorParam'] = '%s' %(job_parmes)
        runxxjob = r.post(urls, data=data)
        if runxxjob.json()['code'] == 200:
            return HttpResponse(json.dumps({
                'code':10000,
                'msg':'执行成功'
            }))
        else:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': 'xxjob请求失败'
            }))

    @classmethod
    @request_verify('post',{'useType':int})
    def xxjob_list(cls,request):
        useType = json_request(request,'useType',int,default=1)
        page = json_request(request,'page',int,default=1)
        limit = json_request(request, 'limit', int, default=20)
        group_name = json_request(request, 'group_name', str, not_null=False,default=None)
        job_name = json_request(request, 'job_name', str, not_null=False, default=None)
        env = json_request(request, 'env', int, not_null=False, default=None)
        if useType == 1:#xxjob列表
            query = Q(status=1)
            if group_name:
                query &= Q(group_name__icontains=group_name)
            if job_name:
                query &= Q(job_name__icontains=job_name)
            if env:
                query &= Q(env=env)
            querys = tuple(models.xxjobMenu.objects.filter(query).values())
            p = Paginator(querys, limit)  # 实例化分页对象
            count = p.count
            logging.info('xxjob任务查询总数{}'.format(p.count))
            result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
            return HttpResponse(json.dumps({
                'count': count,
                'code': 10000,
                'page': page,
                'data': result
            }, cls=DateEncoder, ensure_ascii=False))
        else:
            datas = [{
                'value':1,
                'lable':'联调环境',
                'children':[]
            },
                {
                    'value': 2,
                    'lable': '预发环境',
                    'children':[]
                }]
            for data in datas:
                groupIdList = []
                groupSet = models.xxjobMenu.objects.filter(status=1, env=data['value']).values()
                for group in groupSet:
                    if group['group_id'] in groupIdList:
                        continue
                    dicts = {}
                    dicts['value'] = group['group_id']
                    dicts['leble'] = group['group_name']
                    dicts['children'] = []
                    jobSet = models.xxjobMenu.objects.filter(status=1, env=data['value'],group_id=group['group_id']).values()
                    for job in jobSet:
                        job_dict = {}
                        job_dict['value'] = job['job_id']
                        job_dict['leble'] = job['job_name']
                        dicts['children'].append(job_dict)
                    data['children'].append(dicts)
                    groupIdList.append(group['group_id'])
            return HttpResponse(json.dumps({
                'code':10000,
                'msg':'查询成功',
                'data':datas
            }))



