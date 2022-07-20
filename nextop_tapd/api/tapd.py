# -*- coding:utf-8 -*-
# !/usr/bin/env python
# @FileName  :tapd.py
# @Time      :2021/12/29 15:20
# @Author    :Careslten


import filetype
import os,logging,json
from django.conf import settings
from django.http import HttpResponse
from utils.handle_msg import HandleMsg
from nextop_tapd.models import tapd_push_record,tapd_demand_status,tapd_bug_status,mail_list
import openpyxl
from utils.ding_talk import DingDingSend
from utils.tapdTemplate import TapdTemplate
from utils.tapd_GetConfPush import getConfPush

# 获取一个logger对象
logger = logging.getLogger(__name__)

def keep_tapd_data (ding_return,dict):
    #推送记录表处理为None字符
    for key in list(dict['datas'].keys()):

        if dict['datas'][key] is None:
            dict['datas'][key] = ""

    if ding_return['code'] == 1000:
        dict['datas']["send_status"] = 1
        tapd_push_record.objects.create(**dict['datas'])
        logging.info("记录表创建成功/推送成功")
    elif ding_return['code'] == 1001:
        dict['datas']["send_status"] = 2
        tapd_push_record.objects.create(**dict['datas'])
        logging.info("记录表创建成功/推送失败")
    else:
        dict['datas']["send_status"] = 0
        tapd_push_record.objects.create(**dict['datas'])
        logging.info("记录表创建成功/不推送")

    if dict['msg_type'] == 'demand_yes' or dict['msg_type'] == 'demand_create_yes':
        #
        if tapd_demand_status.objects.filter(demand_all_id=dict['datas']['push_content']['demand_all_id']).exists():
            for key in list(dict['datas']['push_content'].keys()):
                # 删除为空键值对
                if dict['datas']['push_content'][key] == "" or dict['datas']['push_content'][key] is None:
                    logging.info("_+_+_+_____{},{}".format(key, dict['datas']['push_content'][key]))
                    dict['datas']['push_content'].pop(key)
            tapd_demand_status.objects.update_or_create(defaults=dict['datas']['push_content'],
                                                        demand_all_id=dict['datas']['push_content']['demand_all_id'])
        else:
            tapd_demand_status.objects.update_or_create(defaults=dict['datas']['push_content'],
                                                demand_all_id=dict['datas']['push_content']['demand_all_id'])

    elif dict['msg_type'] == "bug_yes" or dict['msg_type'] == 'bug_create_yes':
        if tapd_bug_status.objects.filter(bug_all_id=dict['datas']['push_content']['bug_all_id']).exists():
            for key in list(dict['datas']['push_content'].keys()):
                if dict['datas']['push_content'][key] == "" or dict['datas']['push_content'][key] is None:

                    dict['datas']['push_content'].pop(key)
            logging.info("_+_+_+_____{}".format( dict['datas']['push_content']))
            tapd_bug_status.objects.update_or_create(defaults=dict['datas']['push_content'],
                                                     bug_all_id=dict['datas']['push_content']['bug_all_id'])
        else:
            logging.info("_+_+_+_____{}".format(dict['datas']['push_content']))
            tapd_bug_status.objects.update_or_create(defaults=dict['datas']['push_content'],
                                                     bug_all_id=dict['datas']['push_content']['bug_all_id'])

def retrun_send_group(send_user):
    send_group = []
    send_users = send_user.split(';')
    for user in send_users:
        if user == "":
            break
        try:
            ding_userid = mail_list.objects.filter(tapd_name=user).values('ding_userid')[0]['ding_userid']
            send_group.append(ding_userid)
        except Exception as e:
            logging.error("未找到通知人映射{}".format(user))

    logging.info("通知人:%s", send_group)
    return send_group

def tapdMsgPush(request):
    body = json.loads(request.body)
    getConfPush(body)
    # "解析数据"
    return_msg = HandleMsg.tapd_handle_msg(body)
    # 需求状态变更并推送
    if return_msg['msg_type'] == "demand_yes":
        logger.info("demand回调数据".format(return_msg))
        #通知人
        send_users = retrun_send_group(return_msg['datas']['push_man'])
        # 如果推送人为空，不通知，只插入数据
        if send_users=="":
            ding_codes = {"code": 1002}
            keep_tapd_data(ding_codes, return_msg)
            return HttpResponse(json.dumps({'status': 2, 'msg': '未找到相应推送人'}))

        send_data = {
            "type": return_msg['datas']['type'],
            "name": return_msg['datas']["push_content"]['demand_name'],
            "url": return_msg['datas']["push_content"]['url'],
            "middle": return_msg['datas']["push_content"]['middle'],
            "field": "状态",
            "old_status": return_msg['datas']['old_status'],
            "new_status": return_msg['datas']['new_status'],
            "update_user": return_msg['datas']['create_man'],
            "update_time": return_msg['datas']['push_time'],
            "send_user": send_users,
            'event_id':return_msg['datas']['event_id'],
        }
        logging.info(send_data)
        # 钉钉发送消息，插入数据库
        template_msg = TapdTemplate.bug_demand_status_update(send_data)
        keep_tapd_data(DingDingSend.ding_real_man(template_msg), return_msg)
        return HttpResponse(json.dumps({'status': 1,
                                        'msg': 'ok'}))

    # bug状态变更并推送
    if return_msg['msg_type'] == "bug_yes":
        logger.info("bug状态流转回调数据:{}".format(return_msg['datas']))
        # 通知人
        send_users = retrun_send_group(return_msg['datas']['push_man'])
        # 如果推送人为空，不通知，只插入数据
        if send_users ==[]:
            ding_codes = {"code": 1002}
            keep_tapd_data(ding_codes, return_msg)
            return HttpResponse(json.dumps({'status': 2, 'msg': '未找到相应推送人'}))

        # 推送钉钉通知
        send_data = {
            "type": return_msg['datas']['type'],
            "name": return_msg['datas']['push_content']["bug_name"],
            "url": return_msg['datas']['push_content']['url'],
            "field": "状态",
            "old_status": return_msg['datas']['old_status'],
            "new_status": return_msg['datas']['new_status'],
            "update_user": return_msg['datas']['create_man'],
            "update_time": return_msg['datas']['push_time'],
            "send_user": send_users,
            'event_id': return_msg['datas']['event_id'],
            'middle': return_msg['datas']["push_content"]['bug_level']
        }
        logger.info(send_data)
        # 钉钉发送消息，插入数据库
        keep_tapd_data(DingDingSend.ding_real_man(TapdTemplate.bug_demand_status_update(send_data)), return_msg)
        return HttpResponse(json.dumps({'status': 1,
                                        'msg': 'ok'}))
    # 需求插入数据 ,不进行通知
    if return_msg['msg_type'] == "demand_no":
        ding_codes = {"code": 1002}
        keep_tapd_data(ding_codes, return_msg)
        return HttpResponse(json.dumps({'status': 1,
                                        'msg': 'ok'}))

    # bug插入数据 ,不进行通知
    if return_msg['msg_type'] == "bug_no":
        ding_codes = {"code": 1002}
        keep_tapd_data(ding_codes, return_msg)
        return HttpResponse(json.dumps({'status': 1,
                                        'msg': 'ok'}))



def tapdMsgNewPush(request):
    body = json.loads(request.body)
    getConfPush(body)
    logger.info("新增bug回调信息:{}".format(body))
    #解析回调数据
    return_msg = HandleMsg.tapd_handle_msg(body)
    if return_msg['msg_type'] == "bug_create_yes":
        #推送人
        send_users = retrun_send_group(return_msg['datas']['push_man'])
        # 如果推送人为空，不通知，只插入数据
        if send_users==[]:
            ding_codes = {"code": 1002}
            keep_tapd_data(ding_codes, return_msg)
            return HttpResponse(json.dumps({'status': 1, 'msg': '未找到相应推送人'}))

        # 推送钉钉通知
        send_data = {
            "type": "bug",
            "name": return_msg['datas']['push_content']["bug_name"],
            "url": return_msg['datas']['push_content']['url'],
            "status": return_msg['datas']['new_status'],
            "update_user": return_msg['datas']['create_man'],
            "update_time": return_msg['datas']['push_time'],
            "send_user": send_users,
            'event_id': return_msg['datas']['event_id'],
            'middle': return_msg['datas']["push_content"]['bug_level']
        }
        logger.info("send_data:{}".format(send_data))
        # 钉钉发送消息， 插入数据库
        keep_tapd_data(DingDingSend.ding_real_man(TapdTemplate.bug_demand_create(send_data)),return_msg)
        return HttpResponse(json.dumps({'status': 1,
                                        'msg': 'ok'}))


    if return_msg['msg_type'] == "demand_create_yes":
        #推送人
        send_users = retrun_send_group(return_msg['datas']['push_man'])
        #如果推送人为空，不通知，只插入数据
        if send_users==[]:
            ding_codes = {"code": 1002}
            keep_tapd_data(ding_codes, return_msg)
            return HttpResponse(json.dumps({'status': 2, 'msg': '未找到相应推送人'}))

        # 推送钉钉通知
        send_data = {
            "type": "需求",
            "name": return_msg['datas']['push_content']["demand_name"],
            "url": return_msg['datas']['push_content']['url'],
            "status": return_msg['datas']['new_status'],
            "update_user": return_msg['datas']['create_man'],
            "update_time": return_msg['datas']['push_time'],
            "send_user": send_users,
            'event_id': return_msg['datas']['event_id'],
            "middle": return_msg['datas']["push_content"]['middle'],
        }
        logger.info("send_data:{}".format(send_data))
        #钉钉发送消息插入数据库
        keep_tapd_data(DingDingSend.ding_real_man(TapdTemplate.bug_demand_create(send_data)), return_msg)
        return HttpResponse(json.dumps({'status': 1,
                                        'msg': 'ok'}))

def upload_dingding_mail_list(request):
    file = request.FILES.get('files', None)
    if not file:  # 文件对象不存在
        return HttpResponse(json.dumps({'status': 500, 'msg': '没有文件'}))
    if not pIsAllowedFileSize(file.size):
        return HttpResponse(json.dumps({'status': 501, 'msg': '文件太大'}))
    ext = pGetFileExtension(file)
    if not pIsAllowedfileType(ext):
        return HttpResponse(json.dumps({'msg': '文件类型错误'}))
    if not os.path.exists(settings.FILE_SAVING_PATH):
        os.makedirs(settings.FILE_SAVING_PATH)
    with open(settings.FILE_SAVING_PATH + file.name, "wb+") as f:
        for chunk in file.chunks():
            f.write(chunk)
        f.close()
    wb = openpyxl.load_workbook(filename=settings.FILE_SAVING_PATH + file.name)
    sheet = wb['sheet1']
    datas = tuple(sheet.rows)
    if len(datas[0]) != 8:
        return HttpResponse(json.dumps({'status': 503, 'msg': '表头不正确'}))
    for data in datas[1:]:
        dic = {}
        dic['ding_userid'] = data[0].value  # 员工ID
        dic['ding_name'] = data[1].value  # 姓名
        dic['tapd_name'] = data[2].value  # TAPD对应姓名
        dic['ding_phone'] = data[3].value  # 手机号
        dic['ding_drep'] = data[4].value  # 部门
        dic['ding_is_boss'] = data[5].value  # 是否主管
        dic['ding_boss_id'] = data[6].value  # 直属主管UserID
        dic['ding_status'] = data[7].value  # 激活状态
        try:
            mail_list.objects.update_or_create(defaults=dic, ding_userid=dic['ding_userid'])
        except Exception as e:
            logger.error(str(e))
            return HttpResponse(json.dumps({'status': 504, 'msg': '导入报错'}))

    return HttpResponse(json.dumps({'status': 200, 'msg': '导入成功'}))


# 检测文件
def pGetFileExtension(file):
    rawData = bytearray()
    for c in file.chunks():
        rawData += c
    try:
        ext = filetype.guess_extension(rawData)
        return ext
    except Exception as e:
        logger.error(str(e))
        return None


# 文件类型过滤 只允许上传常用的excel文件
def pIsAllowedfileType(ext):
    if ext in ["xls", 'xlsx', 'csv', 'zip']:
        return True
    return False


# 文件大小限制
# settings.FILE_SIZE_LIMIT
def pIsAllowedFileSize(size):
    limit = settings.FILE_SIZE_LIMIT
    if size < limit:
        return True
    return False