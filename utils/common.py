#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 11:31
# @Author  : Carewn
# @Software: PyCharm

import json
import datetime

class DateEncoder(json.JSONEncoder):
    '''
    返回datetime数据时格式化
    '''
    def default(self,obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj,datetime.date):
            return obj.strftime("%Y-%m-%d")
        else:
            return json.JSONEncoder.default(self, obj)