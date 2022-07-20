# -*- coding: utf-8 -*-
import requests,logging,json
from test_management.models import system_config
from django.conf import settings
import io
import base64
import binascii
import hashlib
import string
import struct
from random import choice
from Crypto.Cipher import AES


logger = logging.getLogger(__name__)

# 获取钉钉token
def get_ding_token():
    ding_info_exist = system_config.objects.filter(name='ding_info').exists()
    if not ding_info_exist:
        url = "https://oapi.dingtalk.com/gettoken?appkey={}&appsecret={}".format(settings.DING_APPKEY,
                                                                                 settings.DING_SECRET)
        return_msg = requests.get(url=url).json()
        sys_info = {
            "name": "ding_info",
            "ext": return_msg['access_token'],
            "remark": "dingding_token",
            "status": "1"
        }
        system_config.objects.update_or_create(defaults=sys_info, name='ding_info')
        return return_msg['access_token']
    return system_config.objects.filter(name='ding_info').values('ext')[0].get('ext')


class DingDingSend():

    '''
    钉钉发送工作消息
    send_data={
    ‘data’：{
            'msg': {'msgtype': "markdown",
                    "markdown": {
                        'title': '’,
                        'text': '‘
                    }},
            "userid_list":
            "agent_id":
    }
    }
    '''
    @classmethod
    def ding_real_man(self,send_data,retry=False):
        ding_token = get_ding_token()
        logger.info("获取ding_token{}".format(ding_token))
        url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"
        logger.info("发送消息内容{}".format(send_data["data"]))
        reqs = requests.post(url=url, json=send_data["data"],headers={
            'x-acs-dingtalk-access-token':ding_token
        }).json()
        if 'message' in reqs.keys():
            #如果还在报错，则重新获取一次token
            if retry == True:
                logger.info("发送消息失败，响应内容--------------------------：{}".format(reqs))
                return {"code": 1001, "msg": "request error", 'error': reqs['message']}
            url = "https://oapi.dingtalk.com/gettoken?appkey={}&appsecret={}".format(settings.DING_APPKEY,
                                                                                     settings.DING_SECRET)
            return_msg = requests.get(url=url).json()
            sys_info = {
                "name": "ding_info",
                "ext": return_msg['access_token'],
                "remark": "dingding_token",
                "status": "1"
            }
            system_config.objects.update_or_create(defaults=sys_info, name='ding_info')
            #标识已经重试
            retry = True
            return self.ding_real_man(send_data,retry)
        logger.info("发送消息成功，响应内容--------------------------：{}".format(reqs))
        return {"code":1000,"msg": "ok"}

    @classmethod
    def ding_real_chat(self,send_data,webhook):
        logger.info("发送消息内容{}".format(send_data["data"]))
        r = requests.post(webhook,json=send_data["data"], headers={"Content-Type": "application/json"})
        if r.json()['errcode'] == 0:
            return {"code":1000,"msg": "ok"}
        else:
            return {'code':500,'error':r.json()['errmsg']}


# 一周统计推送
def ding_week_group(send_data):
    pass


#dingding回调消息加解密类
class DingTalkCrypto:
    def __init__(self, encodingAesKey, key):
        self.encodingAesKey = encodingAesKey
        self.key = key
        self.aesKey = base64.b64decode(self.encodingAesKey + '=')

    def encrypt(self, content):
        """
        加密
        """
        msg_len = self.length(content)
        content = self.generateRandomKey(16) + msg_len.decode() + content + self.key
        contentEncode = self.pks7encode(content)
        iv = self.aesKey[:16]
        aesEncode = AES.new(self.aesKey, AES.MODE_CBC, iv)
        aesEncrypt = aesEncode.encrypt(contentEncode)
        return base64.b64encode(aesEncrypt).decode().replace('\n', '')

    def length(self, content):
        """
        将msg_len转为符合要求的四位字节长度
        """
        l = len(content)
        return struct.pack('>l', l)

    def pks7encode(self, content):
        """
        安装 PKCS#7 标准填充字符串
        """
        l = len(content)
        output = io.StringIO()
        val = 32 - (l % 32)
        for _ in range(val):
            output.write('%02x' % val)
        return bytes(content, 'utf-8') + binascii.unhexlify(output.getvalue())

    def pks7decode(self, content):
        nl = len(content)
        val = int(binascii.hexlify(content[-1].encode()), 16)
        if val > 32:
            raise ValueError('Input is not padded or padding is corrupt')
        l = nl - val
        return content[:l]

    def decrypt(self, content):
        """
        解密数据
        """
        # 钉钉返回的消息体
        content = base64.b64decode(content)
        iv = self.aesKey[:16]  # 初始向量
        aesDecode = AES.new(self.aesKey, AES.MODE_CBC, iv)
        decodeRes = aesDecode.decrypt(content)[20:].decode().replace(self.key, '')
        # 获取去除初始向量，四位msg长度以及尾部corpid
        return self.pks7decode(decodeRes)

    def generateRandomKey(self, size,
                          chars=string.ascii_letters + string.ascii_lowercase + string.ascii_uppercase + string.digits):
        """
        生成加密所需要的随机字符串
        """
        return ''.join(choice(chars) for i in range(size))

    def generateSignature(self, nonce, timestamp, token, msg_encrypt):
        """
        生成签名
        """
        signList = ''.join(sorted([nonce, timestamp, token, msg_encrypt])).encode()
        return hashlib.sha1(signList).hexdigest()


