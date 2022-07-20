# encoding=utf-8
# 自定义分页器 主要是重命名+添加字段, 排序返回
from collections import OrderedDict
from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    page_query_param = "page"       # 前端传参page获得该页的数据
    page_size_query_param = "size"  # 前端传参size限制每页展示数量， 默认是20

    def get_paginated_response(self, data):
        page = self.page.number
        total_num = self.page.paginator.count
        total_page = self.page.paginator.num_pages
        return OrderedDict({"code": 10000, "msg": "查询成功",
                            'page': page,   # 当前页数
                            'size': '',     # 每页展示数据的数量
                            'totalNum': total_num,      # 总页数
                            'totalPage': total_page,    # 总数据数量
                            'data': data})

