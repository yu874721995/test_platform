#!/usr/bin/python
# encoding=utf-8
import os, time, pytest, yaml
import random
import string
from random import randint

import requests
from loguru import logger
from faker import Faker
from datetime import datetime, timedelta, date


class Project:
    dir = ""


def pytest_sessionstart(session):
    Project.dir = session.config.cache.get("project_dir", None)
    if not Project.dir:  # First time run, no pytest_cache
        first_path = os.getcwd()
        test_case = first_path.find("test_case")
        # 是否存在test_case，存在则找到上一层作为项目路径
        if test_case > 0:
            Project.dir = os.path.dirname(first_path)
        else:
            Project.dir = first_path


@pytest.fixture(scope="session")
def config():
    config_path = os.path.join(Project.dir, "conf.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        conf = yaml.load(f.read(), Loader=yaml.FullLoader)
        return conf


@pytest.fixture
def header(config):
    now_time = str(time.time() * 1000 + randint(0, 10000000))
    headers = {'content-type': 'application/json',
               'x-ca-reqid': now_time,
               'x-ca-reqtime': now_time.split('.')[0],
               'cookie': config["cookie"],
               'canary': config["env"]
               }
    return headers


@pytest.fixture()
def query_sql(env_vars):
    def res_sql(sql):
        data_res = env_vars.mysql_engine.select(sql)
        if data_res and len(data_res) == 1:
            # print("数据库查询结果”", i[0], type(i[0]))
            if isinstance(data_res[0][0], int) and len(str(data_res[0][0])) >= 15:
                data = str(data_res[0][0])
                return data
            return data_res[0][0]  # 只取查询到的第1个返回的元组内的值
        elif data_res and len(data_res) > 1:
            res_list = []
            for i in data_res:
                if isinstance(i[0], int) and len(str(i[0])) >= 15:
                    res_list.append(str(i[0]))
                else:
                    res_list.append(i[0])
            return res_list
        # else:
        #     return ''

    return res_sql


@pytest.fixture()
def fake():
    class GetFaker:
        fa = Faker(locale="zh_CN")
        now_time = time.strftime("%Y%m%d%H%M%S", time.localtime())  # 现在时间
        fa_en = Faker()
        en_name = fa_en.name()  # 英文名
        en_address = fa_en.address()  # 英文地址
        name = fa.name()  # 中文名
        address = fa.address()  # 中文地址
        card = fa.credit_card_number()  # 信用卡
        ssn = fa.ssn()  # 身份证
        phone = fa.phone_number()  # 手机号
        email = fa.safe_email()  # 邮箱
        company = fa.company()  # 公司名
        company_name = fa.company_prefix()
        color = fa.color_name()  # 英文颜色
        md5 = fa.md5()  # MD5
        word = fa.word()  # 两字词语
        words = fa.sentence()  # 一段句子
        job = fa.job()  # 工作岗位

        @staticmethod
        def today(fmt="%Y-%m-%d %H:%M:%S"):
            return time.strftime(fmt, time.localtime())  # 现在时间

        @staticmethod
        def now_t(n=13):
            num = 1000 if n == 13 else 1
            return int(round(time.time() * num))  # 现在的时间戳

        @staticmethod
        def number(n=3):
            range_start = 10 ** (n - 1)
            range_end = (10 ** n) - 1
            return random.randint(range_start, range_end)

        @staticmethod
        def str_num(n=5):
            """生成一串指定位数的字符+数组混合的字符串"""
            m = random.randint(1, n)
            a = "".join([str(random.randint(0, 9)) for _ in range(m)])
            b = "".join([random.choice(string.ascii_letters) for _ in range(n - m)])
            return ''.join(random.sample(list(a + b), n))

        @staticmethod
        def last_week(param='start'):
            now = datetime.now()
            last_week_start = now - timedelta(days=now.weekday() + 7)
            last_week_end = now - timedelta(days=now.weekday() + 1)
            week_dict = {'start_time': str(last_week_start.strftime("%Y-%m-%d")) + " 00:00:00",
                         'end_time': str(last_week_end.strftime("%Y-%m-%d")) + " 00:00:00",
                         'start': last_week_start.strftime("%Y-%m-%d"),
                         'end': last_week_end.strftime("%Y-%m-%d")
                         }
            return week_dict[param]

        @staticmethod
        def last_month(param='start'):
            first_day = date(date.today().year, date.today().month - 1, 1)
            last_day = date(date.today().year, date.today().month, 1) - timedelta(1)
            last_day_t = date(date.today().year, date.today().month, 1)
            week_dict = {
                'start': first_day,
                'end': last_day,
                'start_time': first_day.strftime("%Y-%m-%d %H:%M:%S"),
                'end_time': last_day_t.strftime("%Y-%m-%d %H:%M:%S"),
            }
            return week_dict[param]

    return GetFaker


class CaseVars:
    def __init__(self):
        self.vars_ = {}

    def put(self, key, value):
        self.vars_[key] = value

    def get(self, key):
        value = ""
        try:
            value = self.vars_[key]
        except KeyError:
            logger.error(f"CaseVars doesnt have this key: {key}")
        return value


def create_string_number(n):
    """生成一串指定位数的字符+数组混合的字符串"""
    m = random.randint(1, n)
    a = "".join([str(random.randint(0, 9)) for _ in range(m)])
    b = "".join([random.choice(string.ascii_letters) for _ in range(n - m)])
    return ''.join(random.sample(list(a + b), n))


def number(n=1):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return random.randint(range_start, range_end)


@pytest.fixture()
def run_job():
    def run_xxl_job(job_id, env, pod_id=None, job_param=None):
        if env == 1:
            r = reload_job_cookie('test')
            urls = 'http://xxljob-test.nextop.cc/xxl-job-admin/jobinfo/trigger'
        else:
            r = reload_job_cookie('pre')
            urls = 'http://xxljob-pre.nextop.cc/xxl-job-admin/jobinfo/trigger'
        data = {'id': job_id, 'addressList': pod_id}
        if job_param:
            data['executorParam'] = job_param
        try:
            run_res = r.post(urls, data=data)
            if run_res.json()['code'] == 200:
                # print(run_res.json(), "执行成功")
                return "执行成功"
            else:
                return "执行失败"
        except Exception as e:
            print("xxl job 定时任务执行失败", e)

    return run_xxl_job


def reload_job_cookie(env='test'):  # 获取xxl job cookie
    url = 'http://xxljob-{}.nextop.cc/xxl-job-admin/login'.format(env)
    data = {
        'userName': 'admin',
        'password': 'wlbjdyWHYAVd2EBI'
    }
    r = requests.session()
    r.headers.setdefault('content-type', 'application/x-www-form-urlencoded; charset=UTF-8')
    rsp = r.post(url, data=data)
    if rsp.status_code == 200:
        if rsp.json()['code'] == 200:
            return r
        else:
            raise ImportError('获取job-cookie失败')
    else:
        raise ImportError('获取job-cookie失败')

#
# if __name__ == '__main__':
#     job_id1 = 149
#     env1 = 1
#     pop_id1 = 'http://10.244.252.245:9999/'
#     run_job(job_id=job_id1, env=env1, pop_id=pop_id1)
