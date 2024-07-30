# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @Author    :Careslten
import requests
import logging
from nextop_tapd import models
from test_plant.task import registe_job

logger = logging.getLogger(__name__)

@registe_job(task_name='定时更新钉钉通讯录')
def ding_userList():
    # r = return_tapdSession()[0]
    # tapd_project = return_tapdSession()[1]
    url = 'https://service.erp-sit.yintaerp.com/csms/common/getCompanyStaffData'
    data = {
        "currentPage": 1,
        "pageSize": 1000,
        "param": {}
    }
    re = requests.post(url,json=data).json()
    logger.info(re)
    if re.__contains__('data'):
        userlist = re['data']['records']
        for user in userlist:
            try:
                userExist = models.mail_list.objects.filter(ding_userid=user['dingTalkUserId']).exists()
                if not userExist:
                    try:
                        dic = {
                            'tapd_name': user['username'],
                            'ding_name': user['username'],
                            'email':user['email'],
                            'ding_userid': user['dingTalkUserId'],
                            'userIcon':user['userIcon'] if 'userIcon' in user.keys() else '',
                            'ding_phone': user['phone'] if 'phone' in user.keys() else '',
                            'ding_status':'是'
                        }
                        models.mail_list.objects.create(**dic)
                        logger.info('{}钉钉信息入库成功'.format(user['username']))
                    except Exception as e:
                        logger.error('同步钉钉，{}录入数据库失败:{}'.format(user['username'],str(e)))
                        continue
                else:
                    dic = {
                        'ding_name': user['username'],
                        'email': user['email'],
                        'userIcon': user['userIcon'] if 'userIcon' in user.keys() else '',
                        'ding_phone': user['phone'] if 'phone' in user.keys() else '',
                    }
                    models.mail_list.objects.update_or_create(defaults=dic,ding_userid=user['dingTalkUserId'])
                    logger.info('该员工已存在：{},更新信息'.format(user['username']))
            except Exception as e:
                logger.error('同步钉钉，数据解析失败:{}'.format(str(e)))
                continue
    else:
        logger.error('同步钉钉通讯录接口报错：{}'.format(re))