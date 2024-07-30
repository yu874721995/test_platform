import json

import jenkins
import threading

base_config = {
    'url': 'https://newjenkins.yintaerp.com/',
    'username': 'yubei',
    'password': 'Yu19950122'
}
# def dddd(info):
#     print(info['name'])
#     job_info = jenkins_server.get_job_info(info['name'])
#     for build in job_info['builds']:
#         print(build)
# # pa = {"parameter":[{"name":"deployenv","value":"build:sit"},{"name":"action","description":"打包环境的项目，抓紧时间修改","value":"build"},{"name":"audit","value":"no"},{"name":"ytAppVersion","value":""},{"name":"branch","value":"master"},{"name":"branch2","value":""},{"name":"branch3","value":""},{"name":"option","value":""},{"name":"action2","value":""}]}
# jenkins_server = jenkins.Jenkins(**base_config)
# infos = jenkins_server.get_info()
# Thread = []




# build = jenkins_server.build_job(job_name, parameters=pa)
# print(build)
# for info in infos['jobs']:
#     query = {}
#     job_name = 'web-test-platform'  # info['name']
#     query['Assembly_id'] = job_name
#     query['Assembly_name'] = job_name
    # # 获取job信息

    # res = 58#job_info['builds'][0]['number']
    # build_info = jenkins_server.get_build_info(job_name,res,0)
    # # print(json.dumps(build_info))
    # deployenv = None
    # audit = None
    # action = None
    # ytAppVersion = None
    # print(json.dumps(build_info['actions']))
    # for action_query in build_info['actions']:
    #     if action_query.__contains__('_class'):
    #         print('go_1')
    #         if action_query['_class'] == 'hudson.model.ParametersAction':
    #             print('go-2')
    #             parmes = action_query['parameters']
    #             for parme in parmes:
    #                 print(parme)
    #                 if parme['name'] == 'deployenv':
    #                     deployenv = parme['value']
    #                 elif parme['name'] == 'audit':
    #                     audit = parme['value']
    #                 elif parme['name'] == 'action':
    #                     action = parme['value']
    #                 elif parme['name'] == 'ytAppVersion':
    #                     ytAppVersion = parme['value']
    #                 print(deployenv, audit, action, ytAppVersion)
    # print(deployenv,audit,action,ytAppVersion)
    # break
