# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :func_wrap.py
# @Time      :2022/1/4 16:56
# @Author    :Careslten

import logging

logger = logging.getLogger(__name__)

from functools import wraps
def job_exc(func):
    @wraps(func)
    def wrapper(*args,**kwargs):
        logger.info('定时任务开始执行：'+func.__name__)
        return func(*args,**kwargs)
    logger.info('定时任务执行完毕：' + func.__name__)
    return wrapper

