#!/usr/bin/env python 
# -*- coding: utf-8 -*-

import os.path
import time
import logging
import sys
cwd = os.path.dirname(os.path.abspath('.'))
sys.path.insert(0,cwd)
sys.path.append(logging)

class Logger():

    def __init__(self,logger):
        #调用logging中的getLogger方法
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)
        #定义日志的名字和路径
        log_time = time.strftime('%y%m%d%H%M',time.localtime(time.time()))
        log_path = os.path.abspath('.')+'/Public/Logs/'
        # log_path = os.path.dirname(os.path.abspath('.')) + '/Public/Logs/'
        log_name = log_path+str(log_time)+'.log'

        #创建一个Handler 输出到日志文件
        f_handler = logging.FileHandler(log_name,encoding='utf-8',delay=True)
        f_handler.setLevel(logging.INFO)

        #创建一个Handler 输出到控制台，所以此处不用增加参数
        c_handlers = logging.StreamHandler()
        c_handlers.setLevel(logging.INFO)

        #创建一个Formatter ，定义日志的格式
        formatter = logging.Formatter('%(asctime)s-%(name)s-%(levelname)s-%(message)s')
        f_handler.setFormatter(formatter)
        c_handlers.setFormatter(formatter)

        #添加至这个日志方法中
        self.logger.addHandler(f_handler)
        self.logger.addHandler(c_handlers)


    def getlog(self):
        return self.logger
