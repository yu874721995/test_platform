# -*- coding: utf-8 -*-
from datetime import datetime
import json,time,logging
from test_management.models import system_config
from nextop_tapd.models import tapd_bug_status
logger = logging.getLogger(__name__)

class HandleMsg():
    #判断回调是否有对应的key
    @classmethod
    def return_handle_msg(self,handle_datas,all_datas):
        return_msg = ""
        for handle in handle_datas:
            for all_data in all_datas:
                if handle in all_data:
                    return_msg = all_data[handle]
                    return return_msg
        return return_msg

    @classmethod
    def return_project_name(self,project_id):
        import ast
        project_name = ""
        for project in ast.literal_eval(system_config.objects.filter(name='Tapd_project').values()[0]['ext']):
            if project_id in project['id']:
                project_name = project['project_name']
                break
            else:
                project_name = "没有项目名称"
        return project_name

    @classmethod
    def tapd_handle_msg(self,data):
        demand_middle = {
            "4": "High",
            "3": "Middle",
            "2": "Low",
            "1": "Nice To Have"
        }

        # 判断是否为bug更新
        if 'bug::status_change' in data["events"]:
            # 所有数据
            bug_updata_data = data["events"]['bug::status_change']
            # 更新的数据
            bug_new_data = bug_updata_data['new']
            # 旧数据
            bug_old_data = bug_updata_data['old']

            #bug状态获取映射关系
            try:
                bug_status = json.loads(
                    system_config.objects.filter(name="bug_status_" + bug_old_data['project_id']).values('ext')[0][
                        'ext'].replace('\'', '\"'))
                old_status = bug_status[str(bug_old_data['status'])]
                new_status = bug_status[str(bug_new_data['status'])]
            except Exception as e:
                old_status =new_status= "无状态"

            try:
                iteration_id = self.return_handle_msg(['iteration_id'], [bug_new_data,bug_old_data])
                print(iteration_id, bug_old_data['iteration_id'])
                iteration_name = tapd_bug_status.objects.filter(diedai_id=iteration_id).values('diedai')[0]['diedai']
            except Exception as e:
                iteration_name="没有迭代版本"
            print(self.return_handle_msg(['current_owner',"participator"],[bug_new_data]))
            ##插入数据库信息
            bug_msg = {
                "push_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "push_content": {
                    "bug_id": self.return_handle_msg(['id'],[bug_new_data])[-7:],
                    "bug_all_id": self.return_handle_msg(['id'],[bug_new_data]),
                    "bug_name":self.return_handle_msg(['title'],[bug_old_data]),
                    "status": new_status,
                    "name":self.return_handle_msg(["current_owner","participator",'de'],[bug_new_data]),
                    "url": "https://www.tapd.cn/" + bug_old_data['project_id'] + "/bugtrace/bugs/view?bug_id=" +
                           bug_new_data[
                               'id'],
                    "update_time": self.return_handle_msg(['modified'],[bug_new_data,bug_old_data]),
                    "bug_level":self.return_handle_msg(['priority'],[bug_old_data]),
                    "create_Time":self.return_handle_msg(['created'],[bug_old_data]),
                    "ok_man":self.return_handle_msg(['lastmodify'],[bug_old_data]),
                    "ok_Time":self.return_handle_msg(['closed'],[bug_old_data]),
                    "createMan":self.return_handle_msg(['reporter'],[bug_old_data]),
                    'diedai_id': self.return_handle_msg(['iteration_id'], [bug_new_data, bug_old_data]),
                    "diedai":iteration_name,
                    "project_id": self.return_handle_msg(['project_id'],[bug_old_data]),
                    "project_name":self.return_project_name(bug_old_data['project_id'])
                },
                "create_man": self.return_handle_msg(['user'],[data['event']]),
                "push_man": self.return_handle_msg(["current_owner","participator"],[bug_new_data]),
                "old_status": old_status,
                "new_status": new_status,
                "type": "bug",
                "is_new": "0",
                "ext":"bug更新",
                'event_id': data['event']['event_id']
            }
            logger.info("bug_插入数据库信息{}".format(bug_msg))
            # 如果为新或已关闭，不推送钉钉
            if new_status == "接受/处理" or new_status == "已关闭" or new_status == "已验证":
                return_msg = {
                    "msg_type": "bug_no",
                    "datas": bug_msg
                }
                return return_msg

            # 正常返回bug信息，并推送钉钉
            return_msg = {
                "msg_type": "bug_yes",
                "datas": bug_msg
            }

        # 判断是否为需求状态变更
        elif "story::status_change" in data['events'] or "story::update" in data['events']:
            # 需求所有数据
            demand_updata_data = data['events']['story::status_change']
            # 更新数据
            demand_new_data = demand_updata_data['new']
            # 旧数据
            demand_old_data = demand_updata_data['old']

            try:
                demand_status = json.loads(system_config.objects.filter(name='demand_status_'+demand_old_data['workspace_id']).values('ext')[0]['ext'].replace('\'','\"'))
                old_status = demand_status[str(demand_old_data['status'])]
                new_status = demand_status[str(demand_new_data['status'])]
            except Exception as e:
                old_status= new_status = "无状态"

            try:
                iteration_id = self.return_handle_msg(['iteration_id'],[demand_new_data,demand_old_data])
                iteration_name = tapd_bug_status.objects.filter(diedai_id=iteration_id).values('diedai')[0]['diedai']
            except Exception as e:
                iteration_name = "无迭代版本"
            if self.return_handle_msg(['priority'],[demand_old_data]) in demand_middle:
                middle = demand_middle[self.return_handle_msg(['priority'],[demand_old_data])]
            else:
                middle = self.return_handle_msg(['priority'],[demand_old_data])
            # 插入数据库信息
            demand_msg = {
                "push_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "push_content": {
                    "demand_id": self.return_handle_msg(['id'],[demand_new_data])[-7:],
                    "demand_all_id": self.return_handle_msg(['id'],[demand_new_data]),
                    "demand_name": self.return_handle_msg(['name'],[demand_old_data]),
                    "status":new_status,
                    "name":self.return_handle_msg(['owner'],[demand_new_data]),
                    "url": "https://www.tapd.cn/" + demand_old_data['workspace_id'] + "/prong/stories/view/" +
                           demand_new_data[
                               'id'],
                    "update_time":self.return_handle_msg(['modified'],[demand_new_data]),
                    "beginTime":self.return_handle_msg(['created'],[demand_old_data]),
                    "endTime": self.return_handle_msg(['modified'],[demand_new_data]),
                    "createMan":self.return_handle_msg(['creator'],[demand_old_data]),
                    "update_to_user":self.return_handle_msg(['owner'],[demand_new_data]),
                    "iteration_name":iteration_name,
                    "project_id":self.return_handle_msg(['workspace_id'],[demand_old_data]),
                    "project_name":self.return_project_name(demand_old_data['workspace_id']),
                    "middle":middle,
                    "is_del":"1",
                },
                "create_man": self.return_handle_msg(['user'],[data['event']]),
                "push_man": self.return_handle_msg(['owner'],[demand_new_data]),
                "old_status": old_status,
                "new_status": new_status,
                "type": "需求",
                "is_new": "0",
                "ext":"需求更新",
                'event_id': data['event']['event_id']
            }
            logger.info("demand_信息".format(demand_msg))

            return_msg = {
                "msg_type": "demand_yes",
                "datas": demand_msg
            }

        #判断是否为新增bug
        elif "bug::create" in data['events']:
            bug_new_data = data['events']['bug::create']['new']
            try:
                bug_status = json.loads(system_config.objects.filter(name="bug_status_"+data['workspace_id']).values('ext')[0]['ext'].replace('\'','\"'))
                new_status = bug_status[str(bug_new_data['status'])]
            except Exception as e:
                new_status = "无状态"

            try:
                iteration_id = self.return_handle_msg(['iteration_id'],[bug_new_data])
                iteration_name = tapd_bug_status.objects.filter(diedai_id=iteration_id).values('diedai')[0]['diedai']
            except Exception as e:
                iteration_name = "无迭代版本"

            # 插入数据库信息
            bug_msg = {
                "push_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "push_content": {
                    "bug_id": self.return_handle_msg(['id'],[bug_new_data])[-7:],
                    "bug_all_id": self.return_handle_msg(['id'],[bug_new_data]),
                    "bug_name":self.return_handle_msg(['title'],[bug_new_data]),
                    "status": new_status,
                    "name":self.return_handle_msg(['current_owner'],[bug_new_data]),
                    "url": "https://www.tapd.cn/" + bug_new_data['project_id'] + "/bugtrace/bugs/view?bug_id=" +
                           bug_new_data[
                               'id'],

                    "update_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "bug_level":self.return_handle_msg(['priority'],[bug_new_data,data['event']]),
                    "create_Time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "ok_man":"",
                    "ok_Time":"",
                    "createMan":self.return_handle_msg(['reporter'],[bug_new_data]),
                    'diedai_id': self.return_handle_msg(['iteration_id'], [bug_new_data]),
                    "diedai":iteration_name,
                    "project_id": self.return_handle_msg(['project_id'],[bug_new_data]),
                    "project_name":self.return_project_name(bug_new_data['project_id'])
                },
                "create_man":self.return_handle_msg(['user'],[data['event']]),
                "push_man": self.return_handle_msg(['current_owner'],[bug_new_data]),
                "new_status": new_status,
                "type": "bug_create",
                "is_new": "1",
                "ext":"bug新增",
                'event_id': data['event']['event_id']
            }
            return_msg = {
                "msg_type": "bug_create_yes",
                "datas": bug_msg
            }

        elif 'story::create' in data['events']:
            demand_new_data = data['events']['story::create']['new']

            try:
                demand_status = json.loads(system_config.objects.filter(name="demand_status_" + data['workspace_id']).values('ext')[0]['ext'].replace('\'','\"'))
                new_status = demand_status[str(demand_new_data['status'])]
            except Exception as e:
                new_status = "无状态"

            try:
                iteration_id = self.return_handle_msg(['iteration_id'],[demand_new_data])
                iteration_name = tapd_bug_status.objects.filter(diedai_id=iteration_id).values('diedai')[0]['diedai']
            except Exception as e:
                iteration_name = "无迭代版本"

            if self.return_handle_msg(['priority'],[demand_new_data]) in demand_middle:
                middle = demand_middle[self.return_handle_msg(['priority'],[demand_new_data])]
            else:
                middle = self.return_handle_msg(['priority'],[demand_new_data])

            # 插入数据库信息
            demand_msg = {
                "push_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "push_content": {
                    "demand_id": self.return_handle_msg(['id'],[demand_new_data])[-7:],
                    "demand_all_id": self.return_handle_msg(['id'],[demand_new_data]),
                    "demand_name": self.return_handle_msg(['name'],[demand_new_data]),
                    "status":new_status,
                    "name":self.return_handle_msg(['owner'],[demand_new_data]),
                    "url": "https://www.tapd.cn/" + str(demand_new_data['workspace_id']) + "/prong/stories/view/" +
                           str(demand_new_data['id']),
                    "update_time":time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    "beginTime":self.return_handle_msg(['begin'],[demand_new_data]),
                    "endTime": self.return_handle_msg(['due'],[demand_new_data]),
                    "createMan":self.return_handle_msg(['creator'],[demand_new_data]),
                    "update_to_user":self.return_handle_msg(['owner'],[demand_new_data]),
                    "iteration_name":iteration_name,
                    "project_id":self.return_handle_msg(['workspace_id'],[demand_new_data]),
                    "project_name":self.return_project_name(str(demand_new_data['workspace_id'])),
                    "middle": middle,
                    "is_del":"1",
                },
                "create_man": self.return_handle_msg(['user'],[data['event']]),
                "push_man": self.return_handle_msg(['owner'],[demand_new_data]),
                "new_status": new_status,
                "type": "需求",
                "is_new": "1",
                "ext":"需求新增",
                'event_id':data['event']['event_id']
            }

            return_msg = {
                "msg_type": "demand_create_yes",
                "datas": demand_msg
            }
        else:
            return_msg = {{"msg_type": "no"}, {}}
        return return_msg
