# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :tapdTemplate.py
# @Time      :2021/12/29 10:14
# @Author    :Careslten
import time
from datetime import datetime
from django.conf import settings


class TapdTemplate():

    @classmethod
    def bug_demand_status_update(self, pushMsg):
        text = "你有一条新的{}状态更新,请及时处理  \n".format(pushMsg['type']) + \
               "{}标题：[{}]({})  \n".format(pushMsg['type'], pushMsg['name'], pushMsg['url']) + \
               '变更内容：“{}”字段由“{}”更新为"{}"  \n'.format(pushMsg['field'], pushMsg['old_status'],
                                                    pushMsg['new_status']) + \
               '操作人：{}  \n'.format(pushMsg['update_user']) + \
               '操作时间: {}  \n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + \
               '消息id：{}  \n'.format(pushMsg['event_id'])
        if pushMsg['middle'] == "high" or pushMsg['middle'] == "urgent":
            text += '\n 优先级:<font color=\"#FF0000\"> {} </font> (该bug优先级较高，请优先处理)\n'.format(pushMsg['middle'])
        else:
            text += '优先级：{}  \n'.format(pushMsg['middle'])
        return {
            'data': {
                'msgKey': "sampleMarkdown",
                "msgParam": str({
                    'title': '{}提醒'.format(pushMsg['type']),
                    'text': "## Hi,工作辛苦啦 \n>" + "{}".format(text)
                }),
                "userIds": pushMsg['send_user'],
                'robotCode': settings.ROBOT_ID
            }

        }

    @classmethod
    def bug_demand_create(self, pushMsg):
        text = "你有一条新增的{}请及时处理  \n".format(pushMsg['type']) + \
               "{}标题：[{}]({})  \n".format(pushMsg['type'], pushMsg['name'], pushMsg['url']) + \
               '创建人员：{}  \n'.format(pushMsg['update_user']) + \
               '创建时间：{}  \n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + \
               '状态：{}  \n'.format(pushMsg['status']) + \
               '消息id：{}  \n'.format(pushMsg['event_id'])
        if pushMsg['middle'] == "high" or pushMsg['middle'] == "urgent":
            text += '\n 优先级:<font color=\"#FF0000\"> {} </font> (该bug优先级较高，请优先处理)\n'.format(pushMsg['middle'])
        else:
            text += '优先级：{}  \n'.format(pushMsg['middle'])
        return {
            'data': {
                'msgKey': "sampleMarkdown",
                "msgParam": str({
                    'title': '{}提醒'.format(pushMsg['type']),
                    'text': "## Hi,工作辛苦啦 \n>" + "{}".format(text)
                }),
                "userIds": pushMsg['send_user'],
                'robotCode': settings.ROBOT_ID

            }
        }

    @classmethod
    def every_day_push_template(self, pushMsg):
        demand_text = ''
        bug_text = ''
        demand_num = 0
        bug_num = 0
        if not pushMsg['demand']['demand_data'] and not pushMsg['bug']['bug_data']:
            return None
        if pushMsg['demand']['demand_data'] and pushMsg['demand']['demand_data'] != []:
            demand_text = '待处理需求共[{}]({})个:  \n'.format(pushMsg['demand']['demand_count'],
                                                        'https://www.tapd.cn/my_worktable/?from=left_tree_cloud_v2#&filter_close=true')
            for datas in pushMsg['demand']['demand_data']:
                if demand_num == 5:
                    demand_text += '[...查看更多...]({})'.format(
                        'https://www.tapd.cn/my_worktable/?from=left_tree_cloud_v2#&filter_close=true')
                    demand_num += 1
                    continue
                if demand_num > 5:
                    continue
                demand_text += '【{}】[--{}]({})  \n'.format(datas['project_name'], datas['demand_name'], datas['url'])
                demand_num += 1
        if pushMsg['bug']['bug_data'] and pushMsg['bug']['bug_data'] != []:
            bug_text = '待处理缺陷共[{}]({})个:  \n'.format(pushMsg['bug']['bug_count'],
                                                     'https://www.tapd.cn/my_worktable/?from=left_tree_cloud_v2#&filter_close=true')
            for datas in pushMsg['bug']['bug_data']:
                if bug_num == 5:
                    bug_text += '[............查看更多..............]({})'.format(
                        'https://www.tapd.cn/my_worktable/?from=left_tree_cloud_v2#&filter_close=true')
                    bug_num += 1
                    continue
                if bug_num > 5:
                    continue
                bug_text += '【{}】[--{}]({})  \n'.format(datas['project_name'], datas['bug_name'], datas['url'])
                bug_num += 1
        return {'data': {
            'msgKey': "sampleMarkdown",
            "msgParam": str({
                'title': '今日工作提醒-{}'.format(datetime.now().strftime("%Y-%m-%d")),
                'text': '## Dear {} \n>'.format(pushMsg['name']) + \
                        '您在TAPD上有{}项工作需要处理  \n'.format(
                            int(pushMsg['demand']['demand_count']) + int(pushMsg['bug']['bug_count'])) + \
                        '  \n' + \
                        '  \n' + \
                        '{}   \n'.format(demand_text) + \
                        '------   \n' + \
                        '{}'.format(bug_text)
            }),
            "userIds": pushMsg['ding_user_id'],
            'robotCode': settings.ROBOT_ID
        }}

    @classmethod
    def every_chatroom_push_template(self,pushMsg):
        result = {'data': {
            'msgtype': 'markdown',
            "markdown": {
                'title': '项目风险提醒',
                'text': '## 迭代计划:[{}]({})'.format(pushMsg['iteration_name'],pushMsg['iteration_url']) + \
                        '  \n' +
                        '  \n' +
                        '迭代开始时间：{}'.format(pushMsg['iteration_begin_time']) +
                        '  \n' +
                        '迭代计划完成时间：{}'.format(pushMsg['iteration_end_time']) +
                        '  \n' +
                        '当前测试计划：[{}]({}) \n'.format(pushMsg['plant_name'],pushMsg['plant_url']) +
                        '  \n' +
                        '测试计划完成时间：{} \n'.format(pushMsg['plant_end_time']) +
                        '  \n' +
                        '用例条数：[{}]({})条 \n'.format(pushMsg['case_num'],pushMsg['case_url']) +
                        '  \n' +
                        '测试通过率：[{}]({})% \n'.format(pushMsg['test_pass'],pushMsg['case_url']) +
                        '  \n' +
                        '测试执行进度：[{}]({})% \n'.format(pushMsg['test_progress'],pushMsg['case_url']) +
                        '  \n' +
                        '测试剩余时间：{}'.format(pushMsg['plant_time']) +
                        '  \n' +
                        '迭代包含需求：[{}]({})个，目前进行中剩余：[{}]({})个 \n'.format(pushMsg['demand_num'],pushMsg['demand_num_url'],pushMsg['demand_as_num'],pushMsg['demand_as_num_url']) +
                        '  \n' +
                        '迭代包含bug：[{}]({})个,目前待解决：[{}]({})个，严重及以上：[{}]({})个 \n'.format(pushMsg['bug_num'],pushMsg['bug_num_url'],pushMsg['bug_no_num'],pushMsg['bug_no_num_url'],pushMsg['bug_levelLevel_num'],pushMsg['bug_levelLevel_num_url']) +
                        '  \n' +
                        '延期风险：{}'.format(pushMsg['risk'])
            },
            'at': {
                "atMobiles": [], 'isAtAll': True
            }
        }}
        return result

    @classmethod
    def demand_push_template(self, pushMsg):
        return {'data': {
            'msgtype': "markdown",
            "markdown": {
                'title': '项目风险提醒',
                'text': '## 项目风险提醒' + \
                        '  \n' +
                        '延期需求：[{}]({}) \n'.format(pushMsg['demand_name'], pushMsg['demand_url']) +
                        '  \n' +
                        '计划转测时间：<font color=\"#FF0000\">{}</font> \n'.format(pushMsg['plant_begin_Time']) +
                        '  \n' +
                        '当前状态：{} \n'.format(pushMsg['demand_status']) + \
                        '  \n' +
                        '开发人员：{} \n'.format(pushMsg['demand_woman']) + \
                        '  \n' +
                        '所属迭代:[{}]({})'.format(pushMsg['iteration_name'],pushMsg['iteration_url']) + \
                        '  \n' +
                        '迭代开始时间：{}'.format(pushMsg['iteration_begin_time']) +
                        '  \n' +
                        '迭代计划完成时间：{}'.format(pushMsg['iteration_end_time']) +
                        '  \n' +
                        '测试计划：[{}]({}) \n'.format(pushMsg['plant_name'],pushMsg['plant_url'])
            },
            'at': {
                "atMobiles": [], 'isAtAll': True
            }
        }}

    @classmethod
    def bug_risk_push_template(self, pushMsg):
        return {'data': {
            'msgtype': "markdown",
            "markdown": {
                'title': '项目风险提醒',
                'text': '## 项目风险提醒' + \
                        '  \n' +
                        '需求名称：[{}]({}) \n'.format(pushMsg['demand_name'], pushMsg['demand_url']) +
                        '  \n' +
                        '开始时间：{} \n'.format(pushMsg['beginTime']) + \
                        '  \n' +
                        '结束时间：{} \n'.format(pushMsg['endTime']) + \
                        '  \n' +
                        '当前bug数：{}个,未解决：{}个'.format(pushMsg['bugNum'],pushMsg['noNum']) + \
                        '  \n' +
                        '![screenshot]({})'.format(settings.WEB_HOST_NAME + settings.WEB_IMAGE_SERVER_PATH + 'bug{}.png'.format(pushMsg['pic_time']))
            },
            'at': {
                "atMobiles": [], 'isAtAll': True
            }
        }}

    @classmethod
    def excupt_try_chat(self):
        return {'data': {
            'msgtype': "markdown",
            "markdown": {
                'title': '需求流转提醒',
                'text': '## 需求流转提醒测试消息'
            },
            'at': {
                "atMobiles": [], 'isAtAll': True
            }
        }}

    @classmethod
    def excupt_try_man(self, send_user):
        text = "你有一条新的需求状态更新,请及时处理  \n" + \
               "需求标题：测试消息  \n" + \
               '变更内容：“状态”字段由“开发中”更新为"测试中"  \n' + \
               '操作人：test  \n' + \
               '操作时间: 2022-11-11  \n' + \
               '消息id：{}  \n'.format(str(int(time.time())))
        return {
            'data': {
                'msgKey': "sampleMarkdown",
                "msgParam": str({
                    'title': '测试需求提醒',
                    'text': "## Hi,工作辛苦啦 \n>" + "{}".format(text)
                }),
                "userIds": send_user,
                'robotCode': settings.ROBOT_ID
            }

        }

    @classmethod
    def testplatform_demand_status_update_push(self, pushMsg,send_user):
        text = "有一条新的{}{}更新,请及时处理  \n".format(pushMsg['type'],pushMsg['field']) + \
               "{}标题：[{}]({})  \n".format(pushMsg['type'], pushMsg['name'], pushMsg['url']) + \
               '变更内容：“{}”字段由“{}”更新为"{}"  \n'.format(pushMsg['field'], pushMsg['old_data'],
                                                    pushMsg['new_data']) + \
               '操作人：{}  \n'.format(pushMsg['update_user']) + \
               '操作时间: {}  \n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + \
               '处理人: {}  \n '.format(pushMsg['owner']) +  \
               '消息id：{}  \n'.format(pushMsg['event_id'])
        if pushMsg['middle'] == "high" or pushMsg['middle'] == "urgent":
            text += '\n 优先级:<font color=\"#FF0000\"> {} </font> (该bug优先级较高，请优先处理)\n'.format(pushMsg['middle'])
        else:
            text += '优先级：{}  \n'.format(pushMsg['middle'])
        return {
            'data': {
                'msgKey': "sampleMarkdown",
                "msgParam": str({
                    'title': '{}提醒'.format(pushMsg['type']),
                    'text': "## Hi,工作辛苦啦 \n>" + "{}".format(text)
                }),
                "userIds": send_user,
                'robotCode': settings.ROBOT_ID
            }

        }

    @classmethod
    def testplatform_demand_status_update_push_webhook(self,pushMsg):
        return {'data': {
            'msgtype': "markdown",
            "markdown": {
                'title': '需求流转提醒',
                'text': "有一条新的{}{}更新,请及时处理  \n".format(pushMsg['type'],pushMsg['field']) + \
                       "{}标题：[{}]({})  \n".format(pushMsg['type'], pushMsg['name'], pushMsg['url']) + \
                       '变更内容：“{}”字段由“{}”更新为"{}"  \n'.format(pushMsg['field'], pushMsg['old_data'],
                                                            pushMsg['new_data']) + \
                       '操作人：{}  \n'.format(pushMsg['update_user']) + \
                       '操作时间: {}  \n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + \
                       '处理人: {}  \n '.format(pushMsg['owner']) +  \
                       '消息id：{}  \n'.format(pushMsg['event_id']) + \
                       '优先级：{}  \n'.format(pushMsg['middle'])
            },
            'at': {
                "atMobiles": [], 'isAtAll': True
            }
        }}


    @classmethod
    def testplatform_bug_demand_create(self,pushMsg,send_user):
        text = "有一条新增的{}请及时处理  \n".format(pushMsg['type']) + \
               "{}标题：[{}]({})  \n".format(pushMsg['type'], pushMsg['name'], pushMsg['url']) + \
               '创建人员：{}  \n'.format(pushMsg['update_user']) + \
               '创建时间：{}  \n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + \
               '状态：{}  \n'.format(pushMsg['status']) + \
               '消息id：{}  \n'.format(pushMsg['event_id'])
        if pushMsg['middle'] == "high" or pushMsg['middle'] == "urgent":
            text += '\n 优先级:<font color=\"#FF0000\"> {} </font> (该bug优先级较高，请优先处理)\n'.format(pushMsg['middle'])
        else:
            text += '优先级：{}  \n'.format(pushMsg['middle'])
        return {
            'data': {
                'msgKey': "sampleMarkdown",
                "msgParam": str({
                    'title': '{}提醒'.format(pushMsg['type']),
                    'text': "## Hi,工作辛苦啦 \n>" + "{}".format(text)
                }),
                "userIds": send_user,
                'robotCode': settings.ROBOT_ID

            }
        }

    @classmethod
    def testplatform_bug_demand_create_webhook(self, pushMsg):
        return {'data': {
            'msgtype': "markdown",
            "markdown": {
                'title': '需求流转提醒',
                'text': "有一条新增的{}请及时处理  \n".format(pushMsg['type']) + \
                       "{}标题：[{}]({})  \n".format(pushMsg['type'], pushMsg['name'], pushMsg['url']) + \
                       '创建人员：{}  \n'.format(pushMsg['update_user']) + \
                       '创建时间：{}  \n'.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + \
                       '状态：{}  \n'.format(pushMsg['status']) + \
                       '消息id：{}  \n'.format(pushMsg['event_id']) + \
                       '优先级：{}  \n'.format(pushMsg['middle'])
            },
            'at': {
                "atMobiles": [], 'isAtAll': True
            }
        }}


