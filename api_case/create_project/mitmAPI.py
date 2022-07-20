# coding=utf-8
# 脚本抓取接口数据存储到数据库
# mitmdump -q -p 9999 -s mitmAPI.py --ignore-hosts 'https://api.nextop.com' --set block_global=false --no-http2

import json, time, platform
from threading import Thread

import pymysql
import requests

# host 127.0.0.1 10.0.1.56
host_sql = '127.0.0.1' if platform.node() == 'guyude' else '10.0.1.56'
host_name = "api.nextop.com"


def get_env():
    host_url = r"C:\Windows\System32\drivers\etc\hosts"
    with open(host_url, 'r', encoding="utf-8") as f:
        host_data = f.readlines()
        host_ip = ''
        if host_data:
            for i in host_data:
                if 'api.nextop.com' in i and '#' not in i and '-' not in i:
                    host_ip = i.split(' ')[0]
                    break
        # 处理 不同ip对应不同的环境
    if host_ip:
        if "10.0.10.124" in host_ip:
            env = 2  # 10.0.1.124  是预发环境2
        else:
            if "10.0." in host_ip:
                env = 1  # 1 是联调环境
            else:
                env = 0  # 0 未知环境
    else:  # 不配置host 是生产环境
        env = 3
    return host_ip, env


class GetApi:
    def __init__(self, domains):
        self.domains = domains
        self.res_num = 0
        self.ip_env = get_env()
        ip = self.ip_env[0] if self.ip_env[0] else "生产环境"
        self.now_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        print(f"{self.now_time} 开始获取接口数据，本地环境是 {ip}")
        self.account = ''
        self.cookie = ''

    def response(self, flow):
        host = flow.request.host
        status_code = str(flow.response.status_code)
        if self.match(host) and status_code != '404':
            headers = flow.request.headers
            method = flow.request.method
            path = flow.request.path
            body = flow.request.get_text()
            if not self.cookie:
                self.cookie = headers.get('Cookie')
            print("\n----------START----------")
            print("1请求host：", host)
            print("2请求方法、url：", method, path)
            print("3请求状态码 ：", status_code)
            # print("5请求体 body：", body)
            res_text = flow.response.text
            start_time = flow.request.timestamp_start
            elapsed_time = flow.response.timestamp_end - start_time
            print("【接口耗时】：", round(elapsed_time, 3))
            if self.cookie != headers.get('Cookie'):
                self.account = get_account(headers.get('Cookie'))
                print("登录账号", self.account)
            if not self.account or '未返回' in self.account:
                self.account = get_account(headers.get('Cookie'))
                print("登录账号", self.account)

            if res_text:  # 存在返回结果才会存储
                # data_storage(
                #     method, host, path, body, res_text, headers.get('Cookie'),
                #     round(elapsed_time, 3))
                Thread(
                    target=data_storage,
                    args=(method, host, path, body, res_text,
                          self.account,
                          round(elapsed_time, 3),),
                    daemon=True).start()
                self.res_num += 1
                print(f" {self.res_num} ----------已存储 END----------\n")
            else:
                print("----------没有返回结果，不存储!")

    def match(self, url):
        if not self.domains:
            print("必须配置过滤域名!")
            exit(-1)
        for domain in self.domains:
            if domain == url:
                return True
        return False


def data_storage(method, host, path, body, result, account, elapsed):
    # 判断如果请求参数拼接在url中，提取url中参数，转换成字典，url带？&的符号
    params = {}
    if '=' in path and '?' in path:
        path, data = path.split("?")[0], path.split("?")[1]
        if '&' in data:
            data_list = data.split('&')
            for i in data_list:
                k, v = i.split("=")
                params[k] = v
        else:
            k, v = data.split("=")
            params[k] = v
    j_body = params if params else data_handler(body)
    j_result = {"未处理返回结果": result
                } if 'dataAnalysis' in path and 'report/list' in path else data_handler(result)
    assert_res = {'code': j_result.get('code') if j_result.get('code') else "000000"}
    module_name = path.split('/')
    module = module_name[0] if module_name[0] else module_name[1]
    only_api = method + path
    ip_env = get_env()
    # account = get_account(cookie)
    e_sql = f"""insert into `mit_data` SET only_api="{only_api}",req_method="{method}",
    host_name="{host}",module="{module}",url="{path}",single_body="{j_body}",result="{j_result}", status=1,assert_res="{assert_res}",tag=1, cookie="{account}",elapsed={elapsed},ip="{ip_env[0]}",env={ip_env[1]}
"""
    e_sql2 = f"""insert into `mit_data` SET only_api="{only_api}",req_method="{method}",
    host_name="{host}",module="{module}",url="{path}",single_body="{j_body}",result="返回结果写入异常",status=1,assert_res="{assert_res}",tag=1, cookie="{account}", elapsed={elapsed},ip="{ip_env[0]}",env={ip_env[1]}
"""
    execute_sql(e_sql, e_sql2)


def data_handler(data):  # 处理接口请求、响应的数据，转json"
    j_data = {}
    if data:
        if '"null"' in data and "-null" not in data:  # null,  "null",
            data = data.replace('"null"', '"None"')
        # elif 'null' in data and "-null" not in data:
        #     data = data.replace('null', '""')
        if "'" in data:
            data = data.replace("'", "")
        data = data.replace("\\", "").replace('"{', '{').replace('}"', '}')
        data = data.replace('":"[', '": [').replace('": "[', '": [').replace(']"', ']')
        try:
            j_data = json.loads(data)  # 字符串转成字典
        except Exception as e:
            print("转换成json报错", e)
            print("报错data: ", data)
            if "in double quotes" in e:
                pass
            j_data = {"转换成json报错": f"{data}"}
    return j_data


def execute_sql(sql_sentence, sql2):
    conn = pymysql.connect(host=host_sql,
                           port=3306,
                           user="root",
                           passwd="123456",
                           db='nextop_test',
                           charset='utf8')
    cursor = conn.cursor()
    try:
        cursor.execute(sql_sentence)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("数据库连接或插入数据出错：", e)
        # print("sql语句：\n", sql_sentence)
        cursor.execute(sql2)
        conn.commit()
        cursor.close()
        conn.close()


def get_account(cookies):
    now_time = time.time() * 1000
    # id 0.5984545233153422-1654852699385  x-ca-reqtime: 1654852699385
    headers = {'content-type': 'application/json',
               'origin': 'https://saas.nextop.com',
               'referer': 'https://saas.nextop.com/',
               'x-ca-reqid': str(now_time + 0.888),
               'x-ca-reqtime': str(now_time).split('.')[0],  # 时间不带小数点
               'cookie': cookies
               }
    url = 'https://' + host_name
    userinfo = requests.get(url + '/user/user/userInfo', headers=headers).json()
    if userinfo.get("code") == '000000':
        account = userinfo['data']['userInfo']['account']
        return account
    else:
        return "userInfo接口未返回账号"


# ==================================抓包配置==================================
addons = [GetApi([
    host_name,  # 过滤域名
])]
