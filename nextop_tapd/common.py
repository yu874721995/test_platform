import requests
from random import randint
import logging

logger = logging.getLogger(__name__)


def create_bug(project_id, title, description, priority, severity, owner,cookie):
    '''
    :param project_id: 项目id
    :param title: bug标题
    :param description: bug正文，使用str传递html格式文本
    :param priority: 优先级
    :param severity: 严重程度
    :param owner: 处理人
    :param cookie:cookie
    :return:
    '''
    try:
        url = "https://www.tapd.cn/{}/bugtrace/bugs/submit_from_add/0/security?return_url=https%3A%2F%2Fwww.tapd.cn%2Ftapd_fe%2F{}%2Fbug%2Flist".format(
            project_id, project_id
        )
        num = 13951771600000000 + randint(10000000, 99999999)
        payload = {'data[add_bug_token]': str(num),
                   'data[Bug][title]': title,
                   'data[Bug][issue_id]': '',
                   'bug_id': '',
                   'data[Bug][is_new_status]': '0',
                   'data[Bug][is_replicate]': '0',
                   'data[Bug][create_link]': '0',
                   'data[Bug][is_jenkins]': '0',
                   'data[Bug][template_id]': '',
                   'data[Bug][description]': description,
                   'data[is_editor_or_markdown]': '1',
                   'data[BugStoryRelation][BugStoryRelation_relative_id]': '',
                   'data[Bug][version_report]': '',
                   'data[Bug][module]': '备库-物流',
                   'data[Bug][iteration_id]': '',
                   'data[Bug][priority]': priority,
                   'data[Bug][severity]': severity,
                   'data[Bug][current_owner]': owner,
                   'data[nce]': 'true',
                   'data[submit]': '提交&查看',
                   'data[template_id]': '1153004465001000449',
                   'data[draft_id]': '0',
                   'data[return_url]': 'https://www.tapd.cn/tapd_fe/53004465/bug/list&cur_bug_id=',
                   'dsc_token': 'zcIPF7OwkqiPxDbx'}
        headers = {
            'authority': 'www.tapd.cn',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'max-age=0',
            'cookie': cookie,
            'origin': 'https://www.tapd.cn',
            'referer': 'https://www.tapd.cn/{}/bugtrace/bugs/add'.format(project_id),
            'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36'
        }

        response = requests.request("POST", url, headers=headers, data=payload)
        return response
    except Exception as e:
        logger.error('创建失败，失败原因：{}'.format(str(e)))
        return False
