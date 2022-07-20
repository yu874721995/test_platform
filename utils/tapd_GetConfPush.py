from utils.tapdTemplate import TapdTemplate
from nextop_tapd import models
from django.utils import timezone
from test_management.models import system_config
import time
import logging
from utils.ding_talk import DingDingSend

logger = logging.getLogger(__name__)

demand_middle = {
    "4": "High",
    "3": "Middle",
    "2": "Low",
    "1": "Nice To Have"
}


def getConfPush(body):
    project_id = str(body['workspace_id'])
    demand_status = eval(system_config.objects.get(name='demand_status_{}'.format(project_id)).ext)
    exist = models.tapd_project_conf.objects.filter(tapd_project_id=project_id, status=1).exists()
    if not exist:
        return False
    querys = models.tapd_project_conf.objects.filter(tapd_project_id=project_id, status=1).values()
    for query in querys:
        owner_change_push = query['owner_change_push']
        webhook_url = query['webhook_url']
        users = query['users']
        start_time = query['start_time']
        end_time = query['end_time']
        demand_before_status = eval(query['demand_before_status'])
        demand_after_status = eval(query['demand_after_status'])
        type = list(body['events'].keys())[0]
        now_time = timezone.now()
        if start_time and start_time >= now_time:
            continue
        if end_time and end_time <= now_time:
            continue
        if type == 'story::create':
            demand_data = body['events'][type]['new']
            demand_middle_status = demand_data['priority'] if demand_data.__contains__('priority') else ''
            if demand_middle_status == '':
                demand_text = '无'
            else:
                demand_text = demand_middle[demand_middle_status]
            if '9999998' not in demand_before_status:
                if 'newDemand' not in demand_before_status:
                    continue
            if '9999998' not in demand_after_status:
                if 'newDemand' not in demand_after_status:
                    continue
            data = {
                'type': '需求',
                'name': demand_data['name'] if demand_data.__contains__('name') else '',
                'status': demand_status[demand_data['status'] if demand_data.__contains__('status') else '9999998'],
                'url': 'https://www.tapd.cn/{}/prong/stories/view/{}'.format(project_id,
                                                                             demand_data['id']) if demand_data.__contains__(
                    'id') else '',
                'update_user': demand_data['creator'] if demand_data.__contains__('creator') else '',
                'event_id': str(int(time.time())),
                'middle': demand_text
            }
            if users:
                users = eval(users)
                userdata = []
                for user in users:
                    ding_userid = models.mail_list.objects.get(id=user).ding_userid
                    userdata.append(ding_userid)
                logger.info('推送消息：{}，推送人：{}'.format(data, userdata))
                user_data = TapdTemplate.testplatform_bug_demand_create(data, userdata)
                result = DingDingSend.ding_real_man(user_data)
                if result['code'] != 1000:
                    logger.error('发送钉钉消息失败,失败原因:{}'.format(str(result['error'])))
            if owner_change_push == '2' and type == 'story::update':#1为通知，2为不通知
                continue
            else:
                if webhook_url:
                    logger.info('推送消息：{}'.format(data))
                    webhook_data = TapdTemplate.testplatform_bug_demand_create_webhook(data)
                    result = DingDingSend.ding_real_chat(webhook_data, webhook_url)
                    if result['code'] != 1000:
                        logger.error('发送钉钉消息失败,失败原因:{}'.format(str(result['error'])))

        elif type == 'story::update' or type == 'story::status_change':
            demand_old_data = body['events'][type]['old']
            user = body['events'][type]['user']
            demand_new_data = body['events'][type]['new']
            event = body['event']
            demand_middle_status = demand_old_data['priority'] if demand_old_data.__contains__('priority') else ''
            if demand_middle_status == '':
                demand_text = '无'
            else:
                demand_text = demand_middle[demand_middle_status]
            if 'status:fromto' in event: #优先判断是否是状态修改
                field = '状态'
                old_data = event['status:fromto']['from']
                new_data = event['status:fromto']['to']
                if '9999998' not in demand_before_status:
                    if old_data not in demand_before_status:
                        continue
                if '9999998' not in demand_after_status:
                    if new_data not in demand_after_status:
                        continue
                old_data = demand_status[old_data]
                new_data = demand_status[new_data]
            elif 'owner:fromto' in event:
                field = '处理人'
                old_data = ''
                for i in event['owner:fromto']['from']:
                    old_data += ','
                    old_data += i
                old_data = old_data[1:]
                new_data = ''
                for i in event['owner:fromto']['to']:
                    new_data += ','
                    new_data += i
                new_data = new_data[1:]
            else:
                field = '状态'
                old_data = event['status:fromto']['from']
                new_data = event['status:fromto']['to']
            data = {
                'type': '需求',
                'name': demand_old_data['name'] if demand_old_data.__contains__('name') else '',
                'old_data': old_data,
                'new_data': new_data,
                'url': 'https://www.tapd.cn/{}/prong/stories/view/{}'.format(project_id, demand_new_data[
                    'id']) if demand_new_data.__contains__('id') else '',
                'update_user': user,
                'owner': demand_new_data['owner'] if demand_new_data.__contains__('owner') else demand_old_data['owner'] ,
                'field': field,
                'event_id': str(int(time.time())),
                'middle': demand_text
            }
            if users:
                users = eval(users)
                userdata = []
                for user in users:
                    logger.info('推送消息：{}，推送人：{}'.format(data, userdata))
                    ding_userid = models.mail_list.objects.get(id=user).ding_userid
                    userdata.append(ding_userid)
                logger.info('推送消息：{}，推送人：{}'.format(data, userdata))
                user_data = TapdTemplate.testplatform_demand_status_update_push(data, userdata)
                result = DingDingSend.ding_real_man(user_data)
                if result['code'] != 1000:
                    logger.error('发送钉钉消息失败,失败原因:{}'.format(str(result['error'])))
            if owner_change_push == '2' and type == 'story::update':#1为通知，2为不通知
                continue
            else:
                if webhook_url:
                    logger.info('推送消息：{}'.format(data))
                    webhook_data = TapdTemplate.testplatform_demand_status_update_push_webhook(data)
                    result = DingDingSend.ding_real_chat(webhook_data, webhook_url)
                    if result['code'] != 1000:
                        logger.error('发送钉钉消息失败,失败原因:{}'.format(str(result['error'])))
        else:
            continue
