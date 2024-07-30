# test_platform
1、windows部署
（1）安装python，建议版本3.8
（2）更新pip：pip install --upgrade pip
（3）进入项目根目录，下载项目依赖：pip install -r requirements.txt
（4）编辑nextop_backend文件夹下setting.py文件，修改数据库配置（也可直接使用下图示例配置）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'platform',
        'USER': 'root',
        'PASSWORD': '123456',
        'HOST': '123.60.177.70',
        'PORT': '3306',
        'TIME_ZONE': 'Asia/Shanghai',
        'OPTIONS': {
            'init_command': 'SET default_storage_engine=INNODB,character_set_connection=UTF8MB4,'
                            'collation_connection=utf8mb4_unicode_ci;'}
    }
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": ["redis://:123456@123.60.177.70:6379"],
        },
    },
}
（5）检查所有app目录下是否均有migrations文件夹，如无，则创建（如使用示例数据库配置需跳过该步骤）
'test_plant',  # 测试计划
'nextop_tapd', #tapd相关接口
'user',  # 用户模块
'api_case',  # 测试用例模块
'test_management',  # 测试管理
'test_tools' #测试工具
（6）替换fix_files目录下jobstores.py文件至：（django_apscheduler安装目录）C:\Users\lenovo\AppData\Local\Programs\Python\Python38\Lib\site-packages\django_apscheduler\
        替换operations.py文件至：（django安装目录）
C:\Users\lenovo\AppData\Local\Programs\Python\Python38\Lib\site-packages\django\db\backends\mysql\
（7）开始同步数据库，创建字段更改记录：python manage.py makemigrations（如使用示例数据库配置需跳过该步骤）
（8）同步数据库，执行建表：python manage.py migrate（如使用示例数据库配置需跳过该步骤）
（9）启动服务：python manage.py runserver 0.0.0.0:8080
（10）可能出现的错误：
--------自行同步数据库时，可能会出现提示某张表不存在，此时注释test_plant/task.py文件中：
#models.ScheduledTask.objects.filter().update(status=2)

2、docker部署
安装好docker
（1）进入项目根目录，记录dockerfile.prod文件路径
（2）返回上层目录，执行docker build -f  {dockerfile绝对路径} .           ----------------最后有个.，不要遗漏
