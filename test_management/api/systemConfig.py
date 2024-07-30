
import json
import logging
import requests
from test_management import models
from django.http import HttpResponse
from test_management.common import json_request,request_verify
from django.core.paginator import Paginator
from test_management.common import DateEncoder,jwt_token
from django.db.models import Q
r = requests.session()
logger = logging.getLogger(__name__)

class SystemConfig():

    @classmethod
    @request_verify('post',{'name':str,'ext':str,'remark':str})
    def create(cls,reqeust):
        username = jwt_token(reqeust)['username']
        name = json_request(reqeust,'name',str,not_null=False,default=None)
        ext = json_request(reqeust, 'ext')
        remark = json_request(reqeust, 'remark')
        id = json_request(reqeust,'id',default=None)
        if '_tapd_cookie' in name and username not in name:
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '不允许设置其他人的tapd-Cookie信息'
            }))
        try:
            if id:
                models.system_config.objects.update_or_create(defaults={
                    'name':name,
                    'ext':ext,
                    'remark':remark
                },id=id)
            else:
                models.system_config.objects.create(**{
                    'name': name,
                    'ext': ext,
                    'remark': remark
                })
        except Exception as e:
            logger.error('添加配置信息失败:{}'.format(str(e)))
            return HttpResponse(json.dumps({
                'code': 10005,
                'msg': '添加失败'
            }))
        return HttpResponse(json.dumps({
            'code': 10000,
            'msg': '操作成功'
        }))

    @classmethod
    def page(cls,request):
        page = json_request(request,'page',int,default=1)
        limit = json_request(request,'limit',int,default=10)
        name = json_request(request,'name',not_null=False,default=None)
        query = Q(status=1)
        if name:
            query &= Q(name__contains=name)
        querys = models.system_config.objects.filter(query).values()
        p = Paginator(tuple(querys), limit)
        count = p.count
        logging.info('配置信息查询总数{}'.format(p.count))
        result = [] if page not in p.page_range else p.page(page).object_list  # 如果传的页码不在数据的有效页码内，返回空列表
        return HttpResponse(json.dumps({
            'count': count, 'page': page, 'code': 10000, 'items': result
        }, cls=DateEncoder))


