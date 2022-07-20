import json
import logging
import time

from test_plant import models
from django.http import HttpResponse
from django.core.paginator import Paginator
import datetime
from test_tools import models
from test_tools.common import reload_cookie,keys
from django.utils import timezone
from test_management.common import json_request, DateEncoder, jwt_token, request_verify


logger = logging.getLogger(__name__)

class BKCI():

    @classmethod
    @request_verify('post')
    def sendDingdingMsg(cls,request):
        ...