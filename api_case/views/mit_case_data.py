# coding=utf-8
from threading import Thread

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from api_case.models import MitData, Case
from api_case.serializers import MitDataSerializer
from utils.api_response import MyResponse
from utils.pagination import CustomPagination


class MitDataViewSet(ModelViewSet):
    queryset = MitData.objects.all()
    serializer_class = MitDataSerializer

    def list(self, request, *args, **kwargs):
        # 预处理所有数据，如果有用例的。用例状态变成 2
        # def have_case():
        #     query_2 = MitData.objects.filter(status=1)
        #     mit_id = []
        #     for obj in query_2:
        #         case = Case.objects.filter(only_api=obj.only_api)
        #         if case:
        #             mit_id.append(obj.id)
        #     MitData.objects.filter(id__in=mit_id).update(status=2)
        # Thread(target=have_case, args=()).start()

        query = Q()
        host_name = request.GET.get("hostName")
        query &= Q(host_name__icontains=host_name)
        elapsed = request.GET.get('elapsed')
        if elapsed:  # 如果传了耗时时间
            query &= Q(elapsed__gt=elapsed)
        source = request.GET.get('source')
        if source:  # 如果传是否有bug
            query &= Q(source=str(source))
        env = request.GET.get('env')
        if env:  # 如果传环境标签
            query &= Q(env__icontains=env)
        only_api = request.GET.get('only_api')
        if only_api:
            query &= Q(url__icontains=only_api)
        url = request.GET.get('url')
        if url:
            query &= Q(url__icontains=url)
        cookie = request.GET.get('cookie')
        if cookie:
            query &= Q(cookie__icontains=cookie)
        module = request.GET.get('module')
        if module:
            query &= Q(module__icontains=module)
        status_id = request.GET.get('status')
        if status_id:
            query &= Q(status__icontains=status_id)  # 1 无用例。 2有用例
        start_time = request.GET.get('start_time')
        end_time = request.GET.get('end_time')
        if start_time:
            # gte 大于等于某个时间
            query &= Q(created_time__gte=start_time)
        if end_time:
            # lte 小于等于某个时间
            query &= Q(created_time__lte=end_time)
        # .values('only_api').distinct()  去重展示
        queryset = MitData.objects.filter(query).order_by('-id')  # 按照用例id倒序
        cp = CustomPagination()
        page = cp.paginate_queryset(queryset, request=request)
        # page = cp.paginate_queryset(serializer.data, request=request)
        size = cp.get_page_size(request)
        if page is not None:
            serializer = MitDataSerializer(page, many=True)
            data = cp.get_paginated_response(serializer.data)
            data.update({'size': size})
            return Response(data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(data={"code": 10000, "msg": "更新成功"})

    def perform_update(self, serializer):
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return MyResponse(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        instance.delete()
