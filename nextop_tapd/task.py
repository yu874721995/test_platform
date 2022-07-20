# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :task.py
# @Time      :2021/12/29 15:19
# @Author    :Careslten
import json
import time

from django.conf import settings
import requests
from bs4 import BeautifulSoup
from nextop_tapd import models
from utils.tapdTemplate import TapdTemplate
from utils.ding_talk import DingDingSend
import ast
from django.utils import timezone
from django.db import connection
from dateutil.rrule import *
from datetime import datetime,timedelta
import matplotlib.image as mping  # mping用于读取图片
from pylab import *
import matplotlib.pyplot as plt
from test_plant.task import registe_job
from test_management import models as manageModel
from nextop_tapd import models as tapd_models
from test_management.common import DateEncoder


logger = logging.getLogger(__name__)

def return_tapdSession():
    # tapd项目信息
    tapd_project = ast.literal_eval(manageModel.system_config.objects.filter(name='Tapd_project').values()[0]['ext'])
    tapd_session = manageModel.system_config.objects.filter(name='tapd_headers').values()[0]['ext']
    # 定义tapd通用headers
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip,deflate, br',
        'authority': 'www.tapd.cn',
        'scheme': 'https',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'cookie': tapd_session,
        'sec-ch-ua': '"Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': "Windows",
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'x-requested-with': 'XMLHttpRequest',
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
    }
    r = requests.session()
    r.headers = headers
    return r,tapd_project

def get_tapd_pro():
    r = return_tapdSession()[0]
    url = 'https://www.tapd.cn/api/aggregation/user_and_workspace_aggregation/get_user_and_workspace_basic_info?workspace_id=32444113'
    data = r.get(url).json()['data']['my_projects_ret']['data']['my_project']['recently']
    return data



@registe_job(task_name='爬取tapd项目需求')
def tapd_demand():
    '''
    爬取所有tapd项目需求
    :return:
    '''
    # 根据setting中的项目配置循环执行
    r = return_tapdSession()[0]
    tapd_project = return_tapdSession()[1]
    for pro in tapd_project:
        new_status = {}
        project_id = pro['id']
        project_name = pro['project_name']
        logger.info('{}:{}'.format(project_id,project_name))
        # 更新需求状态映射，因为各个项目需求状态设置不一致
        demand_status = r.post(
            'https://www.tapd.cn//api/entity/stories/get_all_fields?location=prong/stories/stories_list&workspace_id={}&selected_workspace_id='.format(
                project_id)).json()['data']['fields']['status']['options']
        for status in demand_status:
            new_status[status['value']] = status['label']
        demand_status_data = {
            'name': 'demand_status_' + project_id,
            'ext': new_status,
            'remark': '{}项目需求状态映射'.format(project_id),
            'status': 1
        }
        logger.info('更新项目需求状态映射关系：{}'.format(demand_status_data['name']))
        manageModel.system_config.objects.update_or_create(defaults=demand_status_data, name=demand_status_data['name'])
        # 删除回收站需求
        lab = r.get('https://www.tapd.cn/{}/recycle_bin/stories_list?'.format(project_id)).text
        lab_soup = BeautifulSoup(lab)
        try:
            indexs = lab_soup.find_all('span', attrs={'class': 'current-page'})[0].text.split('/')[1]
        except:
            indexs = 1
        try:
            lab_trs = lab_soup.find_all('tbody')[0].find_all('tr')
            del_demand = []
            for tr in lab_trs:
                del_demand.append(tr.find_all('input')[0]['data-id'])
            if indexs != 1:
                for index in range(2, int(indexs) + 1):
                    lab = r.get(
                        'https://www.tapd.cn/{}/recycle_bin/stories_list?page={}'.format(project_id, index)).text
                    lab_soup = BeautifulSoup(lab)
                    lab_trs = lab_soup.find_all('tbody')[0].find_all('tr')
                    for tr in lab_trs:
                        del_demand.append(tr.find_all('input')[0]['data-id'])
            models.tapd_demand_status.objects.filter(demand_all_id__in=del_demand, is_del='1').update(is_del='2')
            count = models.tapd_demand_status.objects.filter(demand_all_id__in=del_demand, is_del='1').count()
        except:
            logger.error('缺少{}项目回收站权限'.format(project_name))
        # 拉取需求
        # 需求会一次性返回，无论有多少个，所以无需顺序翻页取
        trs = []
        url = 'https://www.tapd.cn/{}/prong/stories/stories_list?&async=1&perpage=100&page=1&conf_id=1132444113001025123&category_id=0&filter_token=a34de5a7ffc0a5eab127da8da93a136b&export_token=export_cache_a1f1d89929b64129c3a9b8b9b76b01d1&_=1653453429767'.format(project_id)
        list1 = r.get(url)
        soup = BeautifulSoup(list1.text)
        tr_done = soup.find_all(attrs={"class": "tr-story-item rowNOTdone"})
        tr_notdone = soup.find_all(attrs={"class": "tr-story-item rowdone"})
        for s in tr_done:
            trs.append(s)
        for s in tr_notdone:
            trs.append(s)
        next = soup.find_all(attrs={"class": "current-page"})
        if next != []:
            while True:
                page = next[0].text.split(r'/')
                if page[0] == page[1]:
                    break
                nextpage = int(page[0]) + 1
                url = 'https://www.tapd.cn/{}/prong/stories/stories_list?conf_id=1132444113001025123&perpage=100&page={}'.format(
                    project_id,nextpage)
                list1 = r.get(url)
                soup = BeautifulSoup(list1.text)
                tr_done = soup.find_all(attrs={"class": "tr-story-item rowNOTdone"})
                tr_notdone = soup.find_all(attrs={"class": "tr-story-item rowdone"})
                for s in tr_done:
                    trs.append(s)
                for s in tr_notdone:
                    trs.append(s)
                next = soup.find_all(attrs={"class": "current-page"})
        for demand_tr in trs:
            try:
                # 拼装爬取的html数据，需要预先根据账号设置好tapd页面显示字段，后期可更改为预先判断，未设置则自动设置显示字段//已增加初始化功能定义初始字段
                data = {}
                data['demand_id'] = demand_tr.find_all(attrs={'class': 'j-story-title-link-proxy'})[0].text
                data['demand_all_id'] = demand_tr['story_id']
                data['demand_name'] = demand_tr.find_all(attrs={'class': 'j-story-title-link-proxy'})[0]['title']
                data['status'] = demand_tr.find_all('a', attrs={'id': 'story_status_' + data['demand_all_id']})[
                    0].text
                data['name'] = demand_tr.find_all(attrs={'data-editable-field': 'owner'})[0].text
                data['url'] = demand_tr.find_all(attrs={'class': 'j-story-title-link-proxy'})[0]['href']
                try:
                    data['iteration_name'] = \
                        demand_tr.find_all(attrs={'data-editable-field': 'iteration_id'})[0].find_all('a')[0].text
                    data['iteration_id'] = \
                        demand_tr.find_all(attrs={'data-editable-field': 'iteration_id'})[0]['data-editable-value']
                except:
                    data['iteration_name'] = demand_tr.find_all('td')[-8].find_all('span')[0].text
                    data['iteration_id'] = '未知迭代'
                data['project_id'] = project_id
                data['project_name'] = project_name
                data['beginTime'] = demand_tr.find_all(attrs={'data-editable-field': 'begin'})[0].text
                data['endTime'] = demand_tr.find_all(attrs={'data-editable-field': 'due'})[0].text
                data['createMan'] = demand_tr.find_all('td')[-2].find_all('span')[0].text
                data['middle'] = demand_tr.find_all(attrs={'data-editable-field': 'priority'})[0].text
                data['category'] = demand_tr.find_all(attrs={'data-editable-field': 'category_id'})[0].text
                data['is_del'] = '1'
                for key, value in data.items():
                    data[key] = value.replace(' ', '').replace(f'\n', '').replace(f'\r', '').replace(f'\t', '')
                models.tapd_demand_status.objects.update_or_create(defaults=data, demand_all_id=data['demand_all_id'])
                # 如果需求变成已关闭，同步更新钉钉通知
                if data['status'] == '已实现':
                    models.push_chatroom_config.objects.filter(demand_id=data['demand_id']).update(status='2')
            except Exception as e:
                logger.error('{}项目需求拉取任务执行报错:{}'.format(project_name, str(e)))
                continue


@registe_job(task_name='爬取tapd项目bug')
def tapd_bug():
    '''
    爬取所有tapd项目bug
    :return:
    '''
    # 根据setting中的项目配置循环执行
    r = return_tapdSession()[0]
    tapd_project = return_tapdSession()[1]
    for pro in tapd_project:
        project_id = pro['id']
        project_name = pro['project_name']
        num = 1
        # 删除回收站bug
        lab = r.get('https://www.tapd.cn/{}/recycle_bin/bugs_list?'.format(project_id)).text
        lab_soup = BeautifulSoup(lab)
        try:
            indexs = lab_soup.find_all('span', attrs={'class': 'current-page'})[0].text.split('/')[1]
        except:
            indexs = 1
        try:
            lab_trs = lab_soup.find_all('tbody')[0].find_all('tr')
            del_bug = []
            for tr in lab_trs:
                del_bug.append(tr.find_all('input')[0]['data-id'])
            if indexs != 1:
                for index in range(2, int(indexs) + 1):
                    lab = r.get('https://www.tapd.cn/{}/recycle_bin/bugs_list?page={}'.format(project_id, index)).text
                    lab_soup = BeautifulSoup(lab)
                    lab_trs = lab_soup.find_all('tbody')[0].find_all('tr')
                    for tr in lab_trs:
                        del_bug.append(tr.find_all('input')[0]['data-id'])
            models.tapd_bug_status.objects.filter(bug_all_id__in=del_bug, is_del='1').update(is_del='2')
        except:
            logger.error('缺少{}项目回收站权限'.format(project_name))
        # 拉取需求
        while True:
            data = {"workspace_id": "{}".format(project_id), "conf_id": "", "sort_name": "", "order": "",
                    "perpage": 100, "page": num,
                    "selected_workspace_ids": "", "query_token": "", "location": "/bugtrace/bugreports/my_view",
                    "target": "{}/bug/normal".format(project_id), "entity_types": ["bug"], "use_scene": "bug_list",
                    "return_url": "https://www.tapd.cn/tapd_fe/{}/bug/list".format(project_id),
                    "dsc_token": "xGK0QM4y2H1y3nhc"}
            url = 'https://www.tapd.cn/api/aggregation/bug_aggregation/get_bug_fields_userview_and_list'
            querys = r.post(url, json=data).json()
            bug_status = querys['data']['bugs_list_ret']['data']['status_map'][project_id]
            bug_status_data = {
                'name': 'bug_status_' + project_id,
                'ext': bug_status,
                'remark': '{}项目bug状态映射'.format(project_id),
                'status': 1
            }
            manageModel.system_config.objects.update_or_create(defaults=bug_status_data, name=bug_status_data['name'])
            # 拼装爬取内容，bug可以使用接口爬取，稳定性较高
            bug_querys = querys['data']['bugs_list_ret']['data']['bugs_list']
            for bug_query in bug_querys:
                try:
                    bug_query = bug_query['Bug']
                    bug_data = {}
                    bug_data['bug_id'] = bug_query['id'][-7:]
                    bug_data['bug_all_id'] = bug_query['id']
                    bug_data['bug_name'] = bug_query['title']
                    bug_data['status'] = bug_status[bug_query['status']]
                    bug_data['name'] = bug_query['current_owner']
                    bug_data['url'] = 'https://www.tapd.cn/{}/bugtrace/bugs/view?bug_id={}'.format(project_id,
                                                                                                   bug_query['id'])
                    bug_data['bug_level'] = bug_query['severity'] if bug_query.__contains__('severity') else ''
                    bug_data['create_Time'] = bug_query['created'] if bug_query.__contains__('created') else ''
                    bug_data['ok_man'] = bug_query['fixer'] if bug_query.__contains__('fixer') else ''
                    bug_data['ok_Time'] = bug_query['resolved'] if bug_query.__contains__('resolved') else ''
                    bug_data['createMan'] = bug_query['reporter'] if bug_query.__contains__('reporter') else ''
                    try:
                        bug_data['diedai'] = bug_query['iteration_info']['name']
                        bug_data['diedai_id'] = bug_query['iteration_info']['id']
                    except:
                        bug_data['diedai'] = ''
                        bug_data['diedai_id'] = ''

                    bug_data['project_id'] = project_id
                    bug_data['project_name'] = project_name
                    bug_data['demand_id'] = bug_query['BugStoryRelation_relative_id']
                    bug_data['is_del'] = '1'
                    models.tapd_bug_status.objects.update_or_create(defaults=bug_data,
                                                                    bug_all_id=bug_data['bug_all_id'])
                except Exception as e:
                    logger.error('任务执行报错:' + str(e))
                    logger.error('错误json:' + str(bug_query))
                    continue
            if len(bug_querys) < 100:
                break
            num += 1


@registe_job(task_name='爬取tapd项目迭代')
def tapd_iteration():
    '''
    拉取所有迭代信息
    :return:
    '''
    iteration_list = []
    r = return_tapdSession()[0]
    tapd_project = return_tapdSession()[1]
    for pro in tapd_project:
        project_id = pro['id']
        project_name = pro['project_name']
        num = 1
        while True:
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                'Accept-Encoding': 'gzip,deflate, br',
                'authority': 'www.tapd.cn',
                'scheme': 'https',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Cookie': '1679439166_{}_/prong/iterations/index_remember_view=11{}001039316; iter_card_status=; tui_filter_fields=%5B%22title%22%2C%22current_owner%22%2C%22status%22%2C%22priority%22%5D; tapdsession=16578571224c1a172e9e1cdd06125d9f139211ef48b3464a63363209fcd7b6954b486ee4c5; locale=zh_CN; sso-login-token=8826c8c7316feb5e3a9cde95da929c64; __root_domain_v=.tapd.cn; _qddaz=QD.142757857168044; _qddab=3-oxh072.l5lxcptr; _qdda=3-1.1; dsc-token=zyQB4RuCrw9uzGZw; t_u=0167c1d4de3191d1196329b73485b60fdc88e6b37ce339a4a3440cb46d0da2d8319bb247f4b7a23f6f8521d8e226452179691dd30b97d398fda9ad23264e121c111ed4e0e4b0faef%7C1; t_cloud_login=nextop_1134%40163.com; _t_uid=1679439166; _t_crop=67665176; tapd_div=100_2154; iteration_view_type_cookie=card_view; _wt=eyJ1aWQiOiIxNjc5NDM5MTY2IiwiY29tcGFueV9pZCI6IjY3NjY1MTc2IiwiZXhwIjoxNjU3ODU3ODYxfQ%3D%3D.fec9f30ef402f928c773e8fc7e2f449690fd0ee83185ee7b079136536bb40f2d'.format(
                    project_id, project_id),
                'sec-ch-ua': '"Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': "Windows",
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36",
            }
            a = requests.get(
                'https://www.tapd.cn/{}/prong/iterations/get_next_page_iterations?&page={}&limit=20&time1648448052716'.format(
                    project_id, num),
                headers=headers).text
            soup = BeautifulSoup(a)
            divs = soup.find_all(attrs={'class': 'iteration-card'})
            for div in divs:
                data = {}
                try:
                    data['iteration_status'] = '开启' if div.find_all(attrs={'onopen': 'stories_close_moreaction'})[
                        0].text else ""
                except:
                    data['iteration_status'] = '关闭' if div.find_all(attrs={'onopen': 'stories_open_moreaction'})[
                        0].text else ""
                data['iteration_name'] = div.find_all(attrs={'class': 'iteration_title'})[0]['title']
                data['iteration_id'] = div['iteration_id']
                data['iteration_url'] = 'https://tapd.cn' + \
                                        div.find_all('span', attrs={'class': 'link'})[0].find_all('a')[0]['href']
                data['begin_Time'] = div.find_all('span', attrs={'class': 'text'})[0].text.split('~')[0]
                data['end_Time'] = div.find_all('span', attrs={'class': 'text'})[0].text.split('~')[1]
                data['project_id'] = project_id
                data['project_name'] = project_name
                data['is_del'] = '1'
                for key, value in data.items():
                    data[key] = value.replace(' ', '').replace(f'\n', '').replace(f'\r', '').replace(f'\t', '')
                logger.info('爬取到迭代信息：{}项目{}迭代'.format(project_name,data['iteration_name']))
                models.tapd_iteration_status.objects.update_or_create(defaults=data,
                                                                      iteration_id=data['iteration_id'])
                iteration_list.append(data['iteration_id'])
            num += 1
            try:
                soup.find_all(attrs={'id': 'next_page_iterations_link'})[0].text
            except:
                break

    # 标记删除没有了的迭代
    models.tapd_iteration_status.objects.filter().exclude(iteration_id__in=iteration_list).update(is_del='2')
    # 标记删除没有了的迭代对应的通知及统计
    querys = models.tapd_iteration_status.objects.filter().exclude(iteration_id__in=iteration_list).values()
    for query in querys:
        models.push_chatroom_config.objects.filter(iteration_id=query['iteration_id']).update(status='2')


@registe_job(task_name='tapd每日待办推送')
def dingding_everyday_push():
    '''
    每日统计推送
    :param request:
    :return:
    '''
    # 获取mail_list中所有需要发送每日通知的员工名单
    mails = models.mail_list.objects.filter(ding_status='是', tapd_name='余孛').values('tapd_name')
    for man in mails:
        all_data = {}
        name = man.get('tapd_name')
        # 获取该员工名下所有不在已实现中的需求
        querys = models.tapd_demand_status.objects.filter(name__contains=name, is_del='1').exclude(status__in=['已实现']) \
            .values()
        demand_count = models.tapd_demand_status.objects.filter(name__contains=name, is_del='1').exclude(
            status__in=['已实现']).count()
        demand_list = []
        ding_userid = models.mail_list.objects.filter(tapd_name=name, ding_status='是').values('ding_userid')[0]
        for query in tuple(querys):
            demand_list.append(query)
        demand_data = {
            'demand_count': demand_count,
            'demand_data': demand_list
        }
        if demand_count == '0' or demand_count == 0:
            demand_data = {
                'demand_count': 0,
                'demand_data': []
            }
        all_data['demand'] = demand_data
        # 获取该员工名下所有不在已验证和已关闭状态下的bug
        querys = models.tapd_bug_status.objects.filter(name__contains=name, is_del='1').exclude(
            status__in=['已验证', '已关闭']) \
            .values()
        bug_count = models.tapd_bug_status.objects.filter(name__contains=name, is_del='1').exclude(
            status__in=['已验证', '已关闭']).count()
        bug_list = []
        for query in tuple(querys):
            bug_list.append(query)
        bug_data = {
            'bug_count': bug_count,
            'bug_data': bug_list
        }
        if bug_count == '0' or bug_count == 0:
            bug_data = {
                'bug_count': 0,
                'bug_data': []
            }
        all_data['bug'] = bug_data
        all_data['name'] = name
        all_data['ding_user_id'] = [ding_userid.get('ding_userid')]
        # all_data['ding_user_id'] = ['2452174941653090']  # 本地调试
        # 拼装钉钉消息
        send_data = TapdTemplate.every_day_push_template(all_data)
        # 如果钉钉消息正常返回，则发送当日消息
        if send_data:
            result = DingDingSend.ding_real_man(send_data)
            if result['code'] != 1000:
                logger.error('{}每日汇总发送消息失败,失败原因:{}'.format(name, result['error']))
            else:
                logger.info('{}每日汇总消息发送成功'.format(name))


@registe_job(task_name='更新tapd项目配置')
def update_project_and_maillist():
    r = return_tapdSession()[0]
    # tapd_project = return_tapdSession()[1]
    # tapd项目配置信息接口
    url = 'https://www.tapd.cn/api/aggregation/user_and_workspace_aggregation/get_user_and_workspace_basic_info?workspace_id=32444113'
    data = r.get(url).json()['data']['my_projects_ret']['data']['my_project']['recently']
    manageModel.system_config.objects.update_or_create(defaults={
        'name': 'Tapd_project',
        'ext': data,
        'remark': 'tapdtapd项目配置',
        'status': '1'
    }, name='Tapd_project')


@registe_job(task_name='每日风险提醒')
def every_day_chatroom_push():
    '''
    根据配置的迭代触发风险提醒
    :return:
    '''
    querys = models.push_chatroom_config.objects.filter(status='1').values()
    if querys == None:
        logger.info('未配置任何提醒迭代')
        return
    for query in querys:
        data = {}
        risk = 0
        # 查询迭代信息
        iteration_query = models.tapd_iteration_status.objects.filter(iteration_id=query['iteration_id']).values()
        if iteration_query == None:
            logger.error('配置的迭代数据不存在')
            continue
        iteration_query = iteration_query[0]
        data['iteration_name'] = iteration_query['iteration_name']
        data['iteration_url'] = iteration_query['iteration_url']
        data['iteration_begin_time'] = iteration_query['begin_Time']
        data['iteration_end_time'] = iteration_query['end_Time']

        # 查询最新测试计划
        plant_query = models.tapd_testPlant.objects.filter(iteration_id=query['iteration_id'],
                                                           plant_status='开启').order_by('-create_time').values()
        if len(plant_query) == 0:
            logger.info('该迭代:{}未创建测试计划或测试计划已关闭'.format(data['iteration_name']))
            continue
        plant_query = plant_query[0]
        data['plant_name'] = plant_query['plant_name']
        data['plant_url'] = plant_query['plant_url']
        data['plant_end_time'] = plant_query['plant_end_Time']
        data['case_num'] = plant_query['case_num']
        data['case_url'] = 'https://www.tapd.cn/{}/sparrow/test_plan/detail/{}'.format(query['project_id'],
                                                                                       plant_query['plant_big_id'])
        data['test_pass'] = plant_query['test_pass'][:-1]
        data['test_progress'] = plant_query['test_progress'][:-1]
        if plant_query['plant_end_Time'] == '':
            logger.info('该测试计划:{}未维护时间'.format(plant_query['plant_name']))
            continue
        plant_time = int(((int(time.mktime(time.strptime(plant_query['plant_end_Time'], '%Y-%m-%d'))) + (
                3600 * 18)) - int(time.time())) / (3600 * 24))

        # 如果计划完成时间离当前时间大于3天，则不触发任何通知
        if plant_time > 3:
            continue

        data['iteration_text'] = '即将到期'
        if plant_time >= 0:
            data['plant_time'] = '剩余{}天'.format(plant_time)
        else:
            data['plant_time'] = '<font color=\"#FF0000\">已超出计划时间{}天</font>'.format(abs(plant_time))

        iter_time = int(((int(time.mktime(time.strptime(iteration_query['end_Time'], '%Y-%m-%d'))) - int(
            time.time())) + (3600 * 19)) / (3600 * 24))
        # 如果迭代时间已经到了，直接判定已经延期
        if iter_time < 0:
            data['iteration_text'] = '已经延期'
        if plant_time < 0:
            data['risk'] = '<font color=\"#FF0000\">已经延期</font>'

        # 查询需求数
        demand_count = models.tapd_demand_status.objects.filter(iteration_id=query['iteration_id'], is_del='1').count()
        demand_pass = models.tapd_demand_status.objects.filter(iteration_id=query['iteration_id'], is_del='1').exclude(
            status__in=['已实现']).count()
        data['demand_num'] = demand_count
        data['demand_as_num'] = demand_pass
        data['demand_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=StoryandTask'.format(
            query['project_id'], query['iteration_id'])
        data[
            'demand_as_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=StoryandTask&filter_token=d65aa68da8962a90f95359bbf2608fd3'.format(
            query['project_id'], query['iteration_id'])
        # 查询bug数
        bug_num = models.tapd_bug_status.objects.filter(diedai_id=query['iteration_id'], is_del='1').count()
        bug_no_num = models.tapd_bug_status.objects.filter(diedai_id=query['iteration_id'], is_del='1').exclude(
            status__in=['已关闭', '已验证', '已拒绝']).count()
        bug_levelLevel_num = models.tapd_bug_status.objects.filter(diedai_id=query['iteration_id'], is_del='1',
                                                                   bug_level__in=['fatal', 'serious']).exclude(
            status__in=['已关闭', '已验证', '已解决', '已拒绝']).count()
        data['bug_num'] = bug_num
        data['bug_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=Bugs'.format(query['project_id'],
                                                                                                query['iteration_id'])
        data['bug_no_num'] = bug_no_num
        data[
            'bug_no_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=Bugs&filter_token=90112dde8191073cc009e5fdf7f0dbb9'.format(
            query['project_id'], query['iteration_id'])
        data['bug_levelLevel_num'] = bug_levelLevel_num
        data[
            'bug_levelLevel_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=Bugs&filter_token=1e0fbc7de2021b226bfad1fa9657e1fb'.format(
            query['project_id'], query['iteration_id'])

        # 计算风险
        # 未解决的bug数
        if bug_no_num / bug_num > 0.1 or bug_no_num >= 15: risk += 1
        if bug_no_num / bug_num > 0.2 or bug_no_num >= 30: risk += 2
        # 严重以上未解决的bug数
        if bug_levelLevel_num / bug_no_num > 0.2 or bug_levelLevel_num >= 5: risk += 1
        if bug_levelLevel_num / bug_no_num > 0.3 or bug_levelLevel_num >= 10: risk += 2
        # 用例通过率
        if float(data['test_pass']) < 90: risk += 1
        if float(data['test_pass']) < 85: risk += 1.5
        if float(data['test_pass']) < 80: risk += 2
        # 用例执行率
        if float(data['test_progress']) < 95: risk += 1
        if float(data['test_progress']) < 90: risk += 1.5
        if float(data['test_progress']) < 85: risk += 2

        # 反复打开的bug数量占比
        bug_rerun_count = 0
        bug_reruns = models.tapd_push_record.objects.filter(type='bug', new_status='重新打开').values()
        for bug_rerun in bug_reruns:
            exist = models.tapd_bug_status.objects.filter(bug_id=bug_rerun['push_content']['bug_id'],
                                                          iteration_id=query['iteration_id'], is_del='1').exists()
            if exist:
                bug_rerun_count += 1
        if bug_rerun_count != 0:
            if bug_rerun_count / bug_num > 0.05: risk += 1
            if bug_rerun_count / bug_num > 0.1: risk += 1
            if bug_rerun_count / bug_num > 0.15: risk += 1
        # 风险定义
        if not data.__contains__('risk'):
            if risk < 4:
                data['risk'] = '无风险'
            elif risk < 6:
                data['risk'] = '风险一般'
            elif risk < 8:
                data['risk'] = '<font color=\"#FF0000\">风险较高</font>'
            else:
                data['risk'] = '<font color=\"#FF0000\">风险很高</font>'

        # 拼装钉钉消息
        send_data = TapdTemplate.every_chatroom_push_template(data)
        # 如果钉钉消息正常返回，则发送当日消息
        if send_data:
            result = DingDingSend.ding_real_chat(send_data, query['webhook_url'])
            if result['code'] != 1000:
                logger.error('{}迭代提醒消息发送失败,失败原因:{}'.format(data['iteration_name'], result['error']))
            else:
                logger.info('{}迭代提醒消息发送成功'.format(data['iteration_name']))


@registe_job(task_name='爬取tapd项目测试计划')
def tapd_testPlant():
    '''
    获取测试计划
    :return:
    '''
    plant_list = []
    r = return_tapdSession()[0]
    tapd_project = return_tapdSession()[1]
    for pro in tapd_project:
        project_id = pro['id']
        project_name = pro['project_name']
        num = 1
        while True:
            url = 'https://www.tapd.cn/{}/sparrow/test_plan/plan_list?perpage=20&page={}'.format(project_id, num)
            html = r.get(url).text
            soup = BeautifulSoup(html)
            try:
                trs = soup.find_all('tbody')[0].find_all('tr')
            except IndexError:
                logger.error('{}项目没有开通测试计划tab'.format(project_name))
                break
            except not IndexError:
                logger.error('{}项目不知道为啥报错了'.format(project_name))
                break
            ids = ''
            for tr in trs:
                ids += tr['item_id'] + ','
            detail = r.post('https://www.tapd.cn/{}/sparrow/test_plan/get_special_fields_value'.format(project_id),
                            data={
                                'data[test_plan_ids]': ids,
                                'data[special_fields]': 'story_count,tcase_count,passed_rate,executed_rate,case_coverage'
                            }).json()
            for tr in trs:
                data = {}
                data['plant_id'] = tr.find_all(attrs={'class': 'field_id'})[0].find_all('a')[0].text
                data['plant_big_id'] = tr['item_id']
                data['plant_name'] = tr.find_all(attrs={'class': 'field_name'})[0].find_all('a')[0]['title']
                data['plant_status'] = tr.find_all(attrs={'class': 'field_status'})[0].find_all('a')[0]['title']
                data['plant_man'] = tr.find_all(attrs={'class': 'field_owner'})[0].text
                data['plant_url'] = tr.find_all(attrs={'class': 'field_name'})[0].find_all('a')[0]['href']
                data['plant_begin_Time'] = tr.find_all(attrs={'class': 'field_start_date'})[0].text
                data['plant_end_Time'] = tr.find_all(attrs={'class': 'field_end_date'})[0].text
                try:
                    data['category'] = tr.find_all(attrs={'class': 'field_custom_field_1'})[0].text
                except:
                    data['category'] = ''
                try:
                    data['iteration_id'] = tr.find_all(attrs={'class': 'field_iteration_id'})[0].find_all('a')[0][
                                               'href'][-19:]
                    data['iteration_name'] = tr.find_all(attrs={'class': 'field_iteration_id'})[0].find_all('a')[0].text
                except:
                    data['iteration_id'] = ''
                    data['iteration_name'] = ''
                data['project_id'] = project_id
                data['project_name'] = project_name
                data['is_del'] = '1'
                for key, value in data.items():
                    data[key] = value.replace(' ', '').replace(f'\n', '').replace(f'\r', '').replace(f'\t', '')
                data['case_num'] = detail[data['plant_big_id']]['tcase_count']
                data['test_pass'] = detail[data['plant_big_id']]['passed_rate']
                data['test_progress'] = detail[data['plant_big_id']]['executed_rate']
                data['demand_num'] = detail[data['plant_big_id']]['story_count']
                models.tapd_testPlant.objects.update_or_create(defaults=data,
                                                               plant_big_id=data['plant_big_id'])
                plant_list.append(data['plant_big_id'])
            num += 1
            if len(trs) < 20:
                break
    # 标记删除没有了的测试计划
    models.tapd_testPlant.objects.filter().exclude(plant_big_id__in=plant_list).update(is_del='2')


@registe_job(task_name='推送延期需求通知')
def demand_statusPush():
    '''
    推送已延期需求
    :return:
    '''
    webhook_url = 'https://oapi.dingtalk.com/robot/send?access_token=f93ec8c895721bade573b008f6286f68387cefe13011e5e5ff0650b5d39d2f5d'
    iterations = models.tapd_iteration_status.objects.filter(is_del=1, iteration_status='开启').values()
    for iteration in iterations:
        plant_exist = models.tapd_testPlant.objects.filter(iteration_id=iteration['iteration_id'], is_del=1,
                                                           plant_status='开启').exists()
        demand_exist = models.tapd_demand_status.objects.filter(iteration_id=iteration['iteration_id'],
                                                                is_del=1).exists()

        if not plant_exist or not demand_exist:
            logger.info('该迭代没有已生效的测试计划或需求'.format(iteration['iteration_name']))
            continue
        plant = models.tapd_testPlant.objects.filter(iteration_id=iteration['iteration_id'], is_del=1,
                                                     plant_status='开启').values()[0]
        if plant['plant_begin_Time'] == '--' or plant['plant_begin_Time'] == '':
            logger.info('plant:{}没有维护开始时间'.format(plant['plant_name']))
            continue
        demands = models.tapd_demand_status.objects.filter(iteration_id=iteration['iteration_id'], is_del=1).values()
        for demand in demands:
            if demand['status'] not in ['测试中', '待测试', '已发布', '已实现']:
                if demand['beginTime'] == '--' or demand['beginTime'] == '':
                    logger.info('demand:{}没有维护开始时间'.format(demand['demand_name']))
                    continue
                if plant['plant_begin_Time'] <= demand['beginTime']:
                    all_data = {}
                    all_data['iteration_name'] = iteration['iteration_name']
                    all_data['iteration_url'] = iteration['iteration_url']
                    all_data['iteration_begin_time'] = iteration['begin_Time']
                    all_data['iteration_end_time'] = iteration['end_Time']
                    all_data['plant_name'] = plant['plant_name']
                    all_data['plant_url'] = plant['plant_url']
                    all_data['plant_begin_Time'] = plant['plant_begin_Time']
                    all_data['demand_name'] = demand['demand_name']
                    all_data['demand_url'] = demand['url']
                    all_data['demand_status'] = demand['status']
                    all_data['demand_woman'] = demand['name']
                    all_data['ding_user_id'] = ['2452174941653090']  # 本地调试
                    # 拼装钉钉消息
                    send_data = TapdTemplate.demand_push_template(all_data)
                    if send_data:
                        result = DingDingSend.ding_real_chat(send_data, webhook_url)
                        if result['code'] != 1000:
                            logger.error('{}需求延期提醒消息发送失败,失败原因:{}'.format(demand['demand_name'], result['error']))
                        else:
                            logger.info('{}迭代需求延期提醒消息发送成功'.format(demand['demand_name']))


@registe_job(task_name='绑定测试推送webhock配置')
def go():
    '''
    把所有开启的迭代都配上
    :param request:
    :return:
    '''
    itert = models.tapd_iteration_status.objects.filter(is_del=1, iteration_status='开启').values()
    webhook_url = 'https://oapi.dingtalk.com/robot/send?access_token=f93ec8c895721bade573b008f6286f68387cefe13011e5e5ff0650b5d39d2f5d'
    lists = []
    for i in itert:
        lists.append(i['iteration_id'])
        dic = {
            'project_id': i['project_id'],
            'iteration_id': i['iteration_id'],
            'demand_id': '',
            'webhook_url': webhook_url,
            'remark': '',
            'status': '1'
        }
        models.push_chatroom_config.objects.update_or_create(**dic)
    models.push_chatroom_config.objects.filter().exclude(iteration_id__in=lists).update(status='2')

@registe_job(task_name='bug收敛风险提醒')
def bug_risk_push():
    webhook_url = 'https://oapi.dingtalk.com/robot/send?access_token=f93ec8c895721bade573b008f6286f68387cefe13011e5e5ff0650b5d39d2f5d'
    iterations = models.tapd_iteration_status.objects.filter(is_del=1, iteration_status='开启').values()
    for iteration in iterations:
        demand_exist = models.tapd_demand_status.objects.filter(iteration_id=iteration['iteration_id'],
                                                                is_del=1).exists()
        if not demand_exist:
            logger.error('该迭代没有已生效的需求'.format(iteration['iteration_name']))
            continue
        demands = models.tapd_demand_status.objects.filter(iteration_id=iteration['iteration_id'], is_del=1,
                                                           status='测试中').values()
        for demand in demands:
            if demand['beginTime'] == '--' or demand['beginTime'] == '':
                logger.error('demand:{}没有维护开始时间'.format(demand['demand_name']))
                continue
            cursor = connection.cursor()
            cursor.execute(
                "select DATE_FORMAT(create_Time,'%%Y-%%m-%%d') as times,count(*) from tapd_bug where create_Time > %s and create_Time < %s and demand_id = %s GROUP BY times ORDER BY times asc",
                [demand['beginTime'], demand['endTime'], demand['demand_all_id']])
            bugs = cursor.fetchall()  # 该需求的所有bug groupby结果
            if len(bugs) == 0:
                continue
            data = []
            begintime = datetime.datetime.strptime(bugs[0][0], "%Y-%m-%d")
            endtime = datetime.datetime.strptime(demand['endTime'], "%Y-%m-%d")
            days = list(rrule(freq=DAILY, dtstart=begintime, until=endtime, byweekday=(MO, TU, WE, TH, FR)))
            newday = []
            for day in days:
                newday.append(day.strftime("%Y-%m-%d"))
            for day in newday:
                r = []
                for bug in bugs:
                    if day in bug:
                        r = bug
                        data.append(r)
                        break
                if r == []:
                    data.append((day, 0))
            numsfor = work(data)
            newnumsfor = [x for x in numsfor if x != 0]
            long = 0
            if len(newnumsfor) < 3:
                pass
            else:
                for sf in newnumsfor[-3:]:
                    if sf > 1.2 : long += 1
                    if sf > 1.5 or sf < - 0.2: long += 1
                    if sf > 1.8 or sf < 0.1: long += 1
            if long >= 3:
                times = str(int(time.time() * 1000))
                time.sleep(0.5)
                playbug = [bug[1] for bug in bugs]
                playdata = [bug[0] for bug in bugs]
                draw_trend_chart(playdata, playbug, times, demand['demand_name'])
                bug_num = models.tapd_bug_status.objects.filter(demand_id=demand['demand_all_id'], is_del='1').count()
                bug_no_num = models.tapd_bug_status.objects.filter(demand_id=demand['demand_all_id'],
                                                                   is_del='1').exclude(
                    status__in=['已关闭', '已验证', '已拒绝']).count()
                all_data = {}
                all_data['demand_name'] = demand['demand_name']
                all_data['demand_url'] = demand['url']
                all_data['beginTime'] = demand['beginTime']
                all_data['endTime'] = demand['endTime']
                all_data['bugNum'] = bug_num
                all_data['noNum'] = bug_no_num
                all_data['pic_time'] = times
                # 拼装钉钉消息
                send_data = TapdTemplate.bug_risk_push_template(all_data)
                if send_data:
                    result = DingDingSend.ding_real_chat(send_data, webhook_url)
                    if result['code'] != 1000:
                        logger.error('需求：{}bug风险提醒消息发送失败,失败原因:{}'.format(demand['demand_name'], result['error']))
                    else:
                        logger.info('需求：{}bug风险提醒消息发送成功'.format(demand['demand_name']))


def work(data, numsfor=None):
    if numsfor == None:
        numsfor = []
    '''算相差天数'''
    datas = len(data)
    oneNum = data[0][1]  # 第一个日期的bug数
    # 计算理想值
    newdata = []
    for i in range(1, datas):
        time = data[i][0]
        oriNum = oneNum - (i * (oneNum / (datas))) if oneNum - (i * (oneNum / (datas))) != 0 else 0
        newdata.append((time, oriNum))
    # 对比实际值和理想值第一天的数据，无论是否一致，都去掉当天，重新计算
    for x, y in zip(data[1:], newdata):
        if len(data) == 1:
            continue
        elif x[1] == 0 or y[1] == 0:
            numsfor.append(0)
        else:
            numsfor.append(x[1] / y[1])
        work(data[1:], numsfor)
        break
    return numsfor


def draw_trend_chart(dates, y, times, demand_name):
    # 中文乱码解决方法
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体
    plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像是负号'-'显示为方块的问题
    plt.rcParams['font.family'] = ['Arial Unicode MS', 'Microsoft YaHei', 'SimHei', 'sans-serif']
    x = [datetime.datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
    plt.figure(figsize=(12, 6), dpi=160)
    plt.plot(x, y, "r", linewidth=1)
    plt.ylabel("bug数量")  # y轴标签
    plt.title("需求：{}每日bug变化趋势".format(demand_name))  # 标题
    if not os.path.exists(settings.IMAGE_SAVING_PATH):
        os.mkdir(settings.IMAGE_SAVING_PATH)
    plt.savefig(settings.IMAGE_SAVING_PATH + "bug{}.png".format(times))  # 保存图片名称
    lena = mping.imread(settings.IMAGE_SAVING_PATH + 'bug{}.png'.format(times))  # 读取图片文件信息
    lena.shape
    plt.imshow(lena)  # 显示图片
    plt.axis('off')  # 不显示坐标轴
    plt.title("")
    plt.show()  # 显示


@registe_job(task_name='定时更新钉钉通讯录')
def ding_userList():
    r = return_tapdSession()[0]
    # tapd_project = return_tapdSession()[1]
    url = 'https://internal.nextop.com/backgroundUser/user/pageList'
    data = {
        "currentPage": 1,
        "pageSize": 1000,
        "param": {}
    }
    re = r.post(url,json=data).json()
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

@registe_job(task_name='定时更新tapd映射昵称')
def tapd_for_ding():
    '''
    匹配tapd的nickname和钉钉名称
    :return:
    '''
    r = return_tapdSession()[0]
    tapd_project = return_tapdSession()[1]
    for pro in tapd_project:
        lists = []
        project_id = pro['id']
        project_name = pro['project_name']
        url = 'https://www.tapd.cn/{}/settings/team?page=1'.format(project_id)
        html = r.get(url).text
        soup = BeautifulSoup(html)
        try:
            next_page = soup.find_all('span',attrs={'class':'current-page'})
        except:
            logger.error('缺少{}项目成员管理权限'.format(project_name))
            continue
        if next_page:
            all_page = int(next_page[0].text.split('/')[1]) + 1
            for i in range(1,all_page):
                url = 'https://www.tapd.cn/{}/settings/team?page={}'.format(project_id,i)
                html = r.get(url).text
                soup = BeautifulSoup(html)
                lab_trs = soup.find_all('tbody')[0].find_all('tr')
                for tr in lab_trs[1:]:
                    lists.append(tr)
                logger.info('查询{}项目第{}页'.format(project_name,i))
        for tr in lists:
            data = {}
            data['nickname'] = tr.find_all('div', attrs={'class': 'member-user-nick'})[0].find_all('span')[0].text
            data['name'] = tr.find_all('td',attrs={'data-editable-field':'name'})[0].find_all('span')[0].text
            userExist = models.mail_list.objects.filter(ding_name=data['name']).exists()
            if userExist:
                try:
                    models.mail_list.objects.filter(ding_name=data['name']).update(tapd_name=data['nickname'])
                    logging.info('{}更新成功:{}'.format(data['name'],data['nickname']))
                except Exception as e:
                    logger.error("更新tapd昵称失败，失败原因:{}".format(str(e)))
        logger.info('{}项目更新完毕'.format(project_name))

@registe_job(task_name='获取测试计划详情及绑定的测试用例')
def tapd_get_TestCase():
    r = return_tapdSession()[0]
    # tapd_project = return_tapdSession()[1]
    querys = models.tapd_testPlant.objects.filter(plant_status='开启',is_del='1').values()
    update_case_list = []
    update_demand_list = []
    for query in querys:
        plant_id = query['plant_big_id']
        project_id = query['project_id']
        plant_detail_url = 'https://www.tapd.cn/{}/sparrow/test_plan/view/{}'.format(project_id,plant_id)
        html = r.get(plant_detail_url).text
        soup = BeautifulSoup(html)
        case_list_url = 'https://www.tapd.cn' + soup.find_all(attrs={'id':'id-tapd-toolbar'})[0].find_all('a')[0]['href']
        case_html = r.get(case_list_url).text
        case_soup = BeautifulSoup(case_html)
        case_trs = case_soup.find_all(attrs={'class':'tcase_row'})
        demand_trs = case_soup.find_all(attrs={'class':'story_row'})
        case_list = []
        demand_list = []
        for tr in case_trs:
            case_list.append(tr)
        for demand in demand_trs:
            demand_list.append(demand)
        if len(case_trs) != 0:
            begin_id = case_trs[-1]['parent']
        else:
            begin_id = None
        while begin_id:
            if len(case_trs) >= 100:
                case_next_html = r.post(case_list_url,data={
                    'current_tcase_id_with_parent[parent]':begin_id,
                    'current_tcase_id_with_parent[id]':case_trs[-1]['item_id'],
                    'current_tcase_id_with_parent[type]':'categories'

                }).text
                if case_next_html == '':
                    case_next_html = r.post(case_list_url, data={
                        'current_tcase_id_with_parent[parent]': begin_id,
                        'current_tcase_id_with_parent[id]': case_trs[-1]['item_id'],
                        'current_tcase_id_with_parent[type]': 'story'

                    }).text
                case_soup = BeautifulSoup(case_next_html)
                case_trs = case_soup.find_all(attrs={'class': 'tcase_row'})
                demand_trs = case_soup.find_all(attrs={'class': 'story_row'})
                if len(demand_trs) != 0:
                    for demand in demand_trs:
                        demand_list.append(demand)
                if len(case_trs) != 0:
                    begin_id = case_trs[-1]['parent']
                    for tr in case_trs:
                        case_list.append(tr)
                else:
                    break
            else:break
        for case_tr in case_list:
            data = {}
            try:
                data['plant_big_id'] = plant_id
                data['plant_name'] = query['plant_name']
                data['case_id'] = case_tr['item_id']
                data['case_name'] = case_tr.find_all('a',attrs={'id':'tcase_'+ data['case_id']})[0].text or ''
                data['case_url'] = case_tr.find_all('a',attrs={'id':'tcase_'+ data['case_id']})[0]['href'] or ''
                data['case_level'] = case_tr.find_all('td',attrs={'data-editable':'tselect'})[0].text or ''
                data['case_status'] = case_tr.find_all('td',attrs={'data-editable':'tselect'})[1].text or ''
                data['case_owner'] = case_tr.find_all('td',attrs={'data-editable':'userchooser'})[0].title or ''
                data['case_excute'] = case_tr.find_all('td',attrs={'class':'td_status'})[0].find_all('span')[0].text or ''
                data['excute_num'] = case_tr.find_all('td',attrs={'field':'executed_count'})[0].text or ''
                data['bugs'] = case_tr.find_all('td',attrs={'field':'related_bugs'})[0].text or ''
                data['excute_man'] = case_tr.find_all('td',attrs={'field':'executor'})[0].text or ''
                data['demand_id'] = case_tr['parent']
                nowtime = timezone.now()
                for key, value in data.items():
                    data[key] = value.replace(' ', '').replace(f'\n', '').replace(f'\r', '').replace(f'\t', '')
                if data['case_excute'] == '阻塞':
                    data['before_zhusai_Time'] = nowtime
                    data['zhusai_status'] = '1'
                    if models.tapd_TestCase.objects.filter(case_id=data['case_id']).exists():
                        before_zhusai_Time = models.tapd_TestCase.objects.get(case_id=data['case_id']).before_zhusai_Time
                        zhusai_Time = models.tapd_TestCase.objects.get(case_id=data['case_id']).zhusai_Time
                        if before_zhusai_Time:
                            if sumTime(nowtime):
                                data['zhusai_Time'] = zhusai_Time + (nowtime - before_zhusai_Time).seconds
                else:
                    data['before_zhusai_Time'] = None
                    if models.tapd_TestCase.objects.filter(case_id=data['case_id']).exists():
                        before_zhusai_Time = models.tapd_TestCase.objects.get(case_id=data['case_id']).before_zhusai_Time
                        zhusai_Time = models.tapd_TestCase.objects.get(case_id=data['case_id']).zhusai_Time
                        if before_zhusai_Time:
                            if sumTime(nowtime):
                                data['zhusai_Time'] = zhusai_Time + (nowtime - before_zhusai_Time).seconds
                update_case_list.append(data)
            except Exception as e:
                logger.error('更新用例信息失败：{}'.format(str(e)))
                continue
        for demand in demand_list:
            demand_data = {}
            demand_data['demand_all_id'] = demand['item_id']
            demand_data['plant_id'] = plant_id
            for key, value in demand_data.items():
                demand_data[key] = value.replace(' ', '').replace(f'\n', '').replace(f'\r', '').replace(f'\t', '')
            update_demand_list.append(demand_data)
    for case in update_case_list:
        models.tapd_TestCase.objects.update_or_create(defaults=case, case_id=case['case_id'])
    for update_demand in update_demand_list:
        models.tapd_demand_status.objects.filter(demand_all_id=update_demand['demand_all_id']).update(plant_id=update_demand['plant_id'])

@registe_job(task_name='测试质量统计')
def update_bug_statistic():
    plant_querys = tapd_models.tapd_testPlant.objects.filter(is_del=1,plant_status='开启').values().order_by('project_id')
    delete_plant_id = []
    for query in plant_querys:
        delete_plant_id.append(query['plant_big_id'])
        risk_remark = []
        if query['iteration_id'] == None or query['iteration_id'] == "":
            continue
        data = {}
        data['plant_id'] = query['plant_big_id']  # 计划id
        data['plant_name'] = query['plant_name']  # 测试计划名称
        data['plant_url'] = query['plant_url']  # 测试计划url
        data['iteration_id'] = query['iteration_id']  # 迭代id
        data['iteration_name'] = query['iteration_name']  # 迭代名称
        try:
            iteration_query = tapd_models.tapd_iteration_status.objects.get(iteration_id=query['iteration_id'])
        except Exception as e:
            logger.error('该测试计划:{}-绑定的迭代信息:{}-不存在：{}'.format(query['plant_name'],query['iteration_id'],str(e)))
            continue
        data['iteration_url'] = iteration_query.iteration_url  # 迭代url
        data['module'] = query['category']  # 所属模块
        data['start_time'] = query['plant_begin_Time']  # 测试开始时间
        data['end_time'] = query['plant_end_Time']  # 测试结束时间
        data['owner'] = query['plant_man']  # 测试人员
        data['project_id'] = query['project_id']  # 测试人员
        data['status'] = 1
        # 需求数据
        demand_count = tapd_models.tapd_demand_status.objects.filter(
            is_del='1', plant_id=query['plant_big_id']).count()
        data['demand_num'] = demand_count  # 需求总数
        data['demand_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=StoryandTask'.format(
            query['project_id'], query['iteration_id'])
        demand_id_list = [x['demand_all_id'] for x in list(tapd_models.tapd_demand_status.objects.filter(
            is_del='1', plant_id=query['plant_big_id']).values('demand_all_id'))]
        if demand_id_list == []:
            logger.info('该迭代未维护任何需求：{}'.format(query['plant_name']))
            continue
        data['demand_no_test_num'] = tapd_models.tapd_demand_status.objects.filter(
            is_del='1', plant_id=query['plant_big_id']).exclude(
            status__in=['测试中']).count()
        if data['demand_no_test_num'] != 0:
            risk_remark.append({'remark': '还有需求未转测'})
        data['demand_no_test_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=StoryandTask&filter_token=8bc8444db89ec6a37c03432279218287'.format(query['project_id'],query['iteration_id'])
        # bug数据
        bug_num = tapd_models.tapd_bug_status.objects.filter(is_del='1', demand_id__in=demand_id_list).count()
        bug_no_num = tapd_models.tapd_bug_status.objects.filter(is_del='1', demand_id__in=demand_id_list).exclude(
            status__in=['已关闭', '已验证', '已解决', '已拒绝']).count()
        data['bug_num'] = bug_num  # 迭代bug数量
        data['bug_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=Bugs'.format(query['project_id'],
                                                                                                query[
                                                                                                    'iteration_id'])
        data['bug_no_num'] = bug_no_num  # 未解决数量
        data[
            'bug_no_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=Bugs&filter_token=90112dde8191073cc009e5fdf7f0dbb9'.format(
            query['project_id'], query['iteration_id'])

        # 全部严重以上bug数量
        data['bug_all_level_num'] = tapd_models.tapd_bug_status.objects.filter(is_del='1', demand_id__in=demand_id_list,
                                                                               bug_level__in=['fatal',
                                                                                              'serious']).count()

        # 全部bug中严重以上占比
        if data['bug_all_level_num'] != 0 and bug_num != 0:
            data['bug_all_level_num_proportion'] = round(data['bug_all_level_num'] / bug_num,4) * 100  # 占比
        else:
            data['bug_all_level_num_proportion'] = None
        data['bug_all_level_num_url'] = 'https://www.tapd.cn/{}/prong/iterations/view/{}#tab=Bugs&filter_token=1e0fbc7de2021b226bfad1fa9657e1fb'.format(
                query['project_id'], query['iteration_id']) #跳转tapd链接


        # 重复打开的bug
        bug_reruns = tapd_models.tapd_push_record.objects.filter(type='bug', new_status='重新打开').values()
        bugs = []
        bugs_detail = {}
        for bug_rerun in bug_reruns:
            bug_id = eval(bug_rerun['push_content'])['bug_id']
            exist = tapd_models.tapd_bug_status.objects.filter(bug_id=bug_id, demand_id__in=demand_id_list,
                                                               is_del='1').exists()
            if exist and bug_id not in bugs:
                bugs.append(bug_id)
                bugs_detail[bug_id] = 1
            elif exist and bug_id in bugs:
                bugs_detail[bug_id] += 1
        # 重复打开数量
        data['bug_rerun_count'] = len(bugs)

        # 重复打开bug占全部bug的比例
        if bug_num != 0 and bugs != 0:
            data['bug_rerun_count_proportion'] = round(len(bugs) / bug_num,4) * 100 # 重复打开数量占比
        else:
            data['bug_rerun_count_proportion'] = None
        # 用例数据
        data['case_num'] = tapd_models.tapd_TestCase.objects.filter(plant_big_id=query['plant_big_id']).count()
        data['case_url'] = 'https://www.tapd.cn/{}/sparrow/test_plan/detail/{}'.format(query['project_id'],
                                                                                       query['plant_big_id'])
        data['test_pass'] = query['test_pass'][:-1]  # 测试通过率
        data['test_progress'] = query['test_progress'][:-1]  # 测试执行率
        data['blockNum'] = tapd_models.tapd_TestCase.objects.filter(plant_big_id=query['plant_big_id'],
                                                                    case_excute='阻塞').count()  # 阻塞数
        if data['blockNum'] != 0:
            risk_remark.append({'remark': '有阻塞的测试用例'})
        data['before_blockNum'] = tapd_models.tapd_TestCase.objects.filter(plant_big_id=query['plant_big_id'],
                                                                           zhusai_status='1').count()  # 曾经阻塞数
        before_block_data = list(tapd_models.tapd_TestCase.objects.filter(plant_big_id=query['plant_big_id'],
                                                                                  zhusai_status='1').values())  # 阻塞用例详情
        all_block_time = [x['zhusai_Time'] for x in before_block_data]
        times = 0
        if all_block_time != []:
            for all_block in all_block_time:
                times += all_block
        data['before_block_time'] = round(times / 60 / 60,2) if times != 0 else 0  # 累计阻塞时长
        # 测试剩余时间
        data['plant_time'] = int(
            ((int(time.mktime(time.strptime(query['plant_end_Time'], '%Y-%m-%d')))) - int(time.time())) / (3600 * 24))
        # 不足1天按1天算
        if data['plant_time'] == 0:
            data['plant_time'] = 1
        elif data['plant_time'] < 0:
            risk_remark.append({'remark': '测试已经延期'})
        # 延期解决bug数
        yanqi_bug = []
        yanqi_bug_times = []
        all_bug_querys = tapd_models.tapd_bug_status.objects.filter(is_del='1', demand_id__in=demand_id_list).values()
        for all_bug_query in all_bug_querys:
            if all_bug_query['create_Time'] == '--' or all_bug_query['ok_Time'] == '--':
                continue
            bug_create_time = int(time.mktime(time.strptime(all_bug_query['create_Time'], '%Y-%m-%d %H:%M:%S')))
            bug_ok_time = int(time.mktime(time.strptime(all_bug_query['ok_Time'], '%Y-%m-%d %H:%M:%S')))
            bug_middle = all_bug_query['bug_level']
            bug_time = bug_ok_time - bug_create_time
            if bug_middle in ['fatal', 'serious'] and bug_time > 60 * 60 * 4:
                yanqi_bug.append(all_bug_query['bug_id'])
                yanqi_bug_times.append({'bug_id': all_bug_query['bug_id'], 'yanqi_times': bug_time / 60 / 60})
            elif bug_middle not in ['fatal', 'serious'] and bug_time > 60 * 60 * 24:
                yanqi_bug.append(all_bug_query['bug_id'])
                yanqi_bug_times.append({'bug_id': all_bug_query['bug_id'], 'yanqi_times': bug_time / 60 / 60})
        data['yanqi_num'] = len(yanqi_bug)
        if len(yanqi_bug) != 0:
            data['yanqi_num_proportion'] = round(len(yanqi_bug) / bug_num,4) * 100
        else:
            data['yanqi_num_proportion'] = None

        if len(risk_remark) != 0:
            data['risk'] = '有异常信息'
        else:
            data['risk'] = '无异常信息'
        data['riskData'] = json.dumps(risk_remark,cls=DateEncoder)
        # 计算收敛风险
        if query['plant_begin_Time'] == '--' or query['plant_end_Time'] == '':
            logger.error('plant:{}没有维护开始时间'.format(query['plant_name']))
            data['convergence_risk'] = '缺少测试时间，无法计算'
            tapd_models.tapd_bugStatics.objects.update_or_create(defaults=data,plant_id=data['plant_id'])
            continue
        cursor = connection.cursor()
        cursor.execute(
            "select DATE_FORMAT(create_Time,'%%Y-%%m-%%d') as times,count(*) from tapd_bug where create_Time > %s and create_Time < %s  and demand_id in %s GROUP BY times ORDER BY times asc",
            [query['plant_begin_Time'], query['plant_end_Time'], demand_id_list])
        all_bugs = cursor.fetchall()  # 该需求的所有bug groupby结果
        if len(all_bugs) == 0:
            data['convergence_risk'] = '无风险'
            tapd_models.tapd_bugStatics.objects.update_or_create(defaults=data,plant_id=data['plant_id'])
            continue
        long_data = []
        begintime = datetime.datetime.strptime(all_bugs[0][0], "%Y-%m-%d")
        endtime = datetime.datetime.strptime(query['plant_end_Time'], "%Y-%m-%d")
        days = list(rrule(freq=DAILY, dtstart=begintime, until=endtime, byweekday=(MO, TU, WE, TH, FR)))
        newday = []
        for day in days:
            newday.append(day.strftime("%Y-%m-%d"))
        for day in newday:
            r = []
            for bug in all_bugs:
                if day in bug:
                    r = bug
                    long_data.append(r)
                    break
            if r == []:
                long_data.append((day, 0))
        numsfor, liluns_data = works(long_data)
        newnumsfor = [x for x in numsfor if x != 0]
        convergence_risk_data = [
            {'days': long_data[0][0], 'bug_num': long_data[0][1], 'risk_num': 0, 'convergenceNum': 0}]
        for bug_num, risk_num, convergenceNum in zip(long_data[1:], liluns_data, numsfor):
            convergence_risk_data.append({
                'days': bug_num[0],
                'bug_num': bug_num[1],
                'risk_num': risk_num,
                'convergenceNum': convergenceNum
            })
        data['convergence_risk_data'] = convergence_risk_data
        long = 0
        if len(newnumsfor) < 3:
            pass
        else:
            for sf in newnumsfor[-3:]:
                if sf > 1.2: long += 1
                if sf > 1.5 or sf < - 0.2: long += 1
                if sf > 1.8 or sf < 0.1: long += 1
        if long > 3:
            data['convergence_risk'] = '风险很高'
        else:
            data['convergence_risk'] = '无风险'
        tapd_models.tapd_bugStatics.objects.update_or_create(defaults=data,plant_id=data['plant_id'])
    tapd_models.tapd_bugStatics.objects.exclude(plant_id__in=delete_plant_id).update(status=2)#不在列表中的 标记删除


def sumTime(nw=timezone.now(),beforeTime='9:30',afterTime='21:30'):
    hrs = nw.hour
    mins = nw.minute
    secs = nw.second
    zero = timedelta(seconds=secs + mins * 60 + hrs * 3600)
    st = nw - zero  # this take me to 0 hours.
    beforeTime_hours = int(beforeTime.split(":")[0])
    beforeTime_mins = int(beforeTime.split(":")[1])
    afterTime_hours = int(afterTime.split(":")[0])
    afterTime_mins = int(afterTime.split(":")[1])
    time1 = st + timedelta(seconds=beforeTime_hours * 3600 + beforeTime_mins * 60)  # this gives 9:30 AM
    time2 = st + timedelta(seconds=afterTime_hours * 3600 + afterTime_mins * 60)  # this gives 21:30 PM
    if nw >= time1 and nw <= time2:
        return True
    else:
        return False

def works(data, numsfor=None,every_newdata=None):
    if numsfor == None:
        numsfor = []
    if every_newdata == None:
        every_newdata = []
    else:
        every_newdata = every_newdata
    '''算相差天数'''
    datas = len(data)
    oneNum = data[0][1]  # 第一个日期的bug数
    # 计算理想值
    newdata = []
    for i in range(1, datas):
        time = data[i][0]
        oriNum = oneNum - (i * (oneNum / (datas))) if oneNum - (i * (oneNum / (datas))) != 0 else 0
        newdata.append((time, oriNum))
    # 对比实际值和理想值第一天的数据，无论是否一致，都去掉当天，重新计算
    for x, y in zip(data[1:], newdata):
        if len(data) == 1:
            continue
        elif x[1] == 0 or y[1] == 0:
            numsfor.append(0)
        else:
            numsfor.append(x[1] / y[1])
        every_newdata.append(y[1])
        works(data[1:], numsfor,every_newdata)
        break
    return numsfor,every_newdata









