import json
import logging
from test_management.common import request_verify


logger = logging.getLogger(__name__)

class BKCI():

    @classmethod
    @request_verify('post')
    def sendDingdingMsg(cls,request):
        ...