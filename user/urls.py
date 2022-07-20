#!/usr/bin/python
# encoding=utf-8

from django.urls import path
from user import views
from user.api.Roles import RolesView
from user.api.jurisdiction import JurisdictionView

urlpatterns = [
    # 登录
    path(r"login", views.UserLogin.as_view()),
    path(r"roleList",RolesView.lists),
    path(r"createRole",RolesView.create),
    path(r"deleteRole",RolesView.delete),
    path(r"bindUser", RolesView.bindUser),
    path(r"unbindUser", RolesView.unbindUser),
    path(r"jurisdictionList",JurisdictionView.list),
    path(r"jurisdictionAllList",JurisdictionView.allList),
    path(r"updatajurisdiction",JurisdictionView.update),
    path(r"createjurisdiction",JurisdictionView.create),
    path(r"deletejurisdiction",JurisdictionView.delete),
    path(r"userAuthMenu",RolesView.userAuthMenu),
    path(r"userList",RolesView.userList),
    path(r"roleUserList",RolesView.roleUserList),
    path(r"roleJurisdictionList",RolesView.roleJurisdictionList),
]
