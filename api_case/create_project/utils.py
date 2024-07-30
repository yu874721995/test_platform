# encoding=utf-8
import json

import jmespath
import pymysql
# import urllib3
from loguru import logger
from requests import sessions, Response


# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def request_log(req, *args, **kwargs):
    response = req(*args, **kwargs)
    url, params = '', {}
    try:
        for k, v in kwargs.items():
            if 'url' in k:
                url = v
            elif 'json' in k or 'params' in k:
                params = v
        log_dict = {"url": url, "params": params, "response": response.json()}
        print(json.dumps(log_dict, ensure_ascii=False))  # 用例里面的url，参数， 返回结果打印，不可删除
    except AttributeError:
        logger.error("request failed")
    except Exception as e:
        logger.error(e)
    return PyResponse(response)


def request_wrapper(req):
    def send(*args, **kwargs):
        return request_log(req, *args, **kwargs)

    return send


@request_wrapper
def request(method, url, **kwargs):
    with sessions.Session() as session:
        return session.request(method=method, url=url, **kwargs)


class PyResponse(Response):
    def __init__(self, response):
        super().__init__()
        for k, v in response.__dict__.items():
            self.__dict__[k] = v

    def search(self, expression):
        return jmespath.search(expression, self.json())


# class BaseRequest:
#     def __init__(self, clazz):
#         self.case_vars = clazz.case_vars
#
#     def request(self, method, url, **kwargs):
#         response = request(method, url, **kwargs)
#         return PyResponse(response)


# 封装数据库相关
class MyDB:
    def __init__(self, host, port, user, pwd, db):
        self.host, self.port, self.user, self.pwd, self.db, = host, port, user, pwd, db
        self.conn = None
        self.cursor = None

    def select(self, sql):
        try:
            self.conn = pymysql.connect(host=self.host, port=int(self.port), user=self.user, password=self.pwd,
                                        database=self.db, charset='utf8')
            self.cursor = self.conn.cursor()
            if 'select' in sql.lower():
                self.cursor.execute(sql)  # 执行sql语句
                return self.cursor.fetchall()  # 获取所有数据
            else:
                self.cursor.execute(sql)
                self.conn.commit()
        except Exception as e:
            print(f"数据库连接或查询出错: {e}")

    def __del__(self):
        if self.cursor:
            self.cursor.close()
            self.conn.close()
