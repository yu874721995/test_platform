# -*- coding:utf-8 -*-
# !/usr/bin/env python
# @FileName  :tapd.py
# @Time      :2022/01/25 15:20
# @Author    :Careslten



import logging, json
import requests
from django.conf import settings
from nextop_tapd import models
from test_management import models as manageModel
from django.http import HttpResponse
from utils.ding_talk import DingTalkCrypto,get_ding_token
import time

# 获取一个logger对象
logger = logging.getLogger(__name__)


def ding_msg_callback(request):
    body = json.loads(request.body)
    r = requests.session()
    dtc = DingTalkCrypto(settings.ENCODE_ASE_KEY, settings.DING_APPKEY)
    msg = eval(dtc.decrypt(body['encrypt']))
    logger.info('钉钉回调信息:{}'.format(msg))
    if msg['EventType'] == 'user_add_org':
        for user_id in msg['UserId']:
            user = \
                r.post('https://oapi.dingtalk.com/topapi/v2/user/get?access_token={}'.format(get_ding_token()),
                       json={
                           'userid': user_id
                       }).json()
            logger.info('请求用户信息:{}'.format(user))
            if 'result' not in user.keys():
                if user['sub_code'] == '40014':
                    url = "https://oapi.dingtalk.com/gettoken?appkey={}&appsecret={}".format(settings.DING_APPKEY,
                                                                                             settings.DING_SECRET)
                    token = requests.get(url=url).json()['access_token']
                    user_detail = \
                        r.post('https://oapi.dingtalk.com/topapi/v2/user/get?access_token={}'.format(token),
                               json={
                                   'userid': user_id
                               }).json()['result']
                    try:
                        manageModel.system_config.objects.filter(name='ding_info').update(ext=token)
                    except:
                        logger.error('更新token失败')
                else:
                    logger.error('获取用户信息失败，失败原因：{}'.format(user['errmsg']))
                    continue
            else:
                user_detail = user['result']
            logger.info('查询新增人员{}信息：{}'.format(user_detail['name'], user_detail))
            dic = {
                'tapd_name': user_detail['name'],
                'ding_name': user_detail['name'],
                'ding_userid': user_detail['userid'],
                'ding_phone': user_detail['mobile'] if 'mobile' in user_detail.keys() else '',
                'ding_drep': '',
                'ding_is_boss': '',
                'ding_boss_id': '',
                'ding_status': '是'}
            models.mail_list.objects.create(**dic)
            logger.info('{}钉钉信息入库成功'.format(user_detail['name']))
    elif msg['EventType'] == 'user_leave_org':
        for user_id in msg['UserId']:
            models.mail_list.objects.filter(ding_userid=user_id).update(ding_status='否')
            user = models.mail_list.objects.filter(ding_userid=user_id).exists()
            if user:
                username = models.mail_list.objects.filter(ding_userid=user_id).values()[0]['ding_name']
                logger.info('{}离职了'.format(username))
            else:
                logger.info('离职员工不存在')
    encrypt = dtc.encrypt('success')  # 加密数据
    timestamp = str(int(round(time.time())))  # 时间戳 (秒)
    nonce = dtc.generateRandomKey(8)  # 随机字符串
    # 生成签名
    signature = dtc.generateSignature(nonce, timestamp, settings.DING_TOKEN, encrypt)
    # 构造返回数据
    new_data = {
        'msg_signature': signature,
        'timeStamp': timestamp,
        'nonce': nonce,
        'encrypt': encrypt
    }
    logger.info('回调钉钉数据{}'.format(new_data))
    return HttpResponse(json.dumps(new_data))
