# !/usr/bin/env python
# -*- coding:utf-8 -*-
# @FileName  :routings.py
# @Time      :2022/7/8 16:07
# @Author    :Careslten

from django.urls import re_path
from test_tools.api import BKCI_tool

# websocket的路由配置
websocket_urlpatterns = [
    re_path("websocket/bk_ci", BKCI_tool.ChatConsumer.as_asgi()),
]