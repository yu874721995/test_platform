from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import UpdateRowsEvent, WriteRowsEvent
import threading
from test_plant import models
import logging
import os

logger = logging.getLogger(__name__)

if not os.environ.__contains__('MYSQL_HOST'):
    mysql_settings = {
        'host': '10.0.1.56',
        'port': 3306,
        'user': 'root',
        'passwd': '123456'
    }
    # 监听数据库
    db_schemas = ['nextop_test']
    # 同步数据库
    sync_schemas = 'nextop_test'
else:
    mysql_settings = {
        'host': os.getenv('MYSQL_HOST'),
        'port': int(os.getenv('MYSQL_PORT')),
        'user': os.getenv('MYSQL_USER'),
        'passwd': os.getenv('MYSQL_PASSWORD')
    }
    # 监听数据库
    db_schemas = ['nextop_test_platform']
    # 同步数据库
    sync_schemas = 'nextop_test_platform'
# 监听数据表
listen_tables = ['django_apscheduler_djangojobexecution']
# 待处理数据队列
wait_handle_queue = []

def main():
    # 实例化binlog 流对象
    stream = BinLogStreamReader(
        connection_settings=mysql_settings,
        server_id=1979092845,  # slave标识，唯一
        blocking=True,  # 阻塞等待后续事件
        # 设定只监控写操作：增、删、改
        only_schemas=db_schemas,
        only_tables=listen_tables,
        freeze_schema=True,
        only_events=[
            # DeleteRowsEvent,
            UpdateRowsEvent,
            WriteRowsEvent
        ]
    )
    logger.info('定时任务增改事件监听启动...')
    for binlogevent in stream:
        try:
            for row in binlogevent.rows:
                event = {
                    "schema": binlogevent.schema,
                    "table": binlogevent.table,
                    "primary_key": binlogevent.primary_key,
                    "status": "wait"
                }
                if isinstance(binlogevent, UpdateRowsEvent):
                    event["action"] = "update"
                    event["data"] = row["after_values"]  # 注意这里不是values
                    job_id = event["data"]['job_id']
                    run_time = event['data']['run_time']
                    models.ScheduledExecution.objects.filter(job_id=job_id,run_time=run_time).update(
                        **{
                            'status':event["data"]['status'],
                            'exception':event["data"]['exception'],
                            'duration':event["data"]['duration'],
                            'finished':event["data"]['finished'],
                            'traceback':event["data"]['traceback']
                        }
                    )
                elif isinstance(binlogevent, WriteRowsEvent):
                    event["action"] = "insert"
                    event["data"] = row["values"]
                    job_id = event["data"]['job_id']
                    run_time = event['data']['run_time']
                    models.ScheduledExecution.objects.create(**{
                        'status': event["data"]['status'],
                        'job_id':job_id,
                        'run_time':run_time,
                        'exception': event["data"]['exception'],
                        'duration': event["data"]['duration'],
                        'finished': event["data"]['finished'],
                        'traceback': event["data"]['traceback']
                    })
        except Exception as e:
            logger.error(str(e))


def work():
    try:
        threading.Thread(target=main).start()
    except:
        logger.error("Error: 无法启动线程")