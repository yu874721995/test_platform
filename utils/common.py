#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 11:31
# @Author  : Carewn
# @Software: PyCharm

import boto3,os,datetime,json
from django.conf import settings
from loguru import logger

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

class S3_client:
    '''s3上传封装'''
    def __init__(self):
        self.region_name = settings.CN_REGION_NAME
        self.access_key = settings.CN_S3_AKI
        self.secret_key = settings.CN_S3_SAK
        self.bucket_name = settings.BUCKET_NAME
        self.s3 = boto3.client('s3', region_name=self.region_name,
                          aws_access_key_id=self.access_key, aws_secret_access_key=self.secret_key
                          )

    def upload_files(self,path_local, path_s3):
        """
        上传（重复上传会覆盖同名文件）
        :param path_local: 本地路径
        :param path_s3: s3路径
        """
        logger.info(f'Start upload files.')

        if not self.upload_single_file(path_local, path_s3):
            logger.error(f'Upload files failed.')

        logger.info(f'Upload files successful.')

    def upload_single_file(self,src_local_path, dest_s3_path):
        """
        上传单个文件
        :param src_local_path:
        :param dest_s3_path:
        :return:
        """
        try:
            with open(src_local_path, 'rb') as f:
                self.s3.upload_fileobj(f, self.bucket_name, dest_s3_path)
        except Exception as e:
            logger.error(f'Upload data failed. | src: {src_local_path} | dest: {dest_s3_path} | Exception: {e}')
            return False
        logger.info(f'Uploading file successful. | src: {src_local_path} | dest: {dest_s3_path}')
        return True

    def download_zip(self,path_s3, path_local):
        """
        下载
        :param path_s3:
        :param path_local:
        :return:
        """
        retry = 0
        while retry < 3:  # 下载异常尝试3次
            logger.info(f'Start downloading files. | path_s3: {path_s3} | path_local: {path_local}')
            try:
                self.s3.download_file(self.bucket_name, path_s3, path_local)
                file_size = os.path.getsize(path_local)
                logger.info(f'Downloading completed. | size: {round(file_size / 1048576, 2)} MB')
                break  # 下载完成后退出重试
            except Exception as e:
                logger.error(f'Download zip failed. | Exception: {e}')
                retry += 1

        if retry >= 3:
            logger.error(f'Download zip failed after max retry.')

    def get_files_list(self,Prefix=None):
        """
        查询
        :param start_after:
        :return:
        """
        logger.info(f'Start getting files from s3.')
        try:
            if Prefix is not None:
                all_obj = self.s3.list_objects_v2(Bucket=self.bucket_name, Prefix=Prefix)

                # 获取某个对象的head信息
                # obj = s3.head_object(Bucket=BUCKET_NAME, Key=Prefix)
                # logger.info(f"obj = {obj}")
            else:
                all_obj = self.s3.list_objects_v2(Bucket=self.bucket_name)

        except Exception as e:
            logger.error(f'Get files list failed. | Exception: {e}')
            return

        contents = all_obj.get('Contents')
        logger.info(f"--- contents = {contents}")
        if not contents:
            return

        file_name_list = []
        for zip_obj in contents:
            zip_name = zip_obj['Key']
            file_name_list.append(zip_name)

        logger.info(f'Get file list successful.')

        return file_name_list

    def delete_s3_zip(self,path_s3):
        """
        删除
        :param path_s3:
        :param file_name:
        :return:
        """
        try:
            self.s3.delete_object(Bucket=self.bucket_name, Key=path_s3)
        except Exception as e:
            logger.error(f'Delete s3 file failed. | Exception: {e}')
            return False
        logger.info(f'Delete s3 file Successful. | path_s3 = {path_s3}')
        return True