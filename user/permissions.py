#!/usr/bin/python
# encoding=utf-8

from rest_framework.permissions import BasePermission

from user.models import UserRole


class IsTester(BasePermission):
    def has_permission(self, request, view):
        user_id = request.user.id
        role_id = UserRole.objects.get(user_id=user_id).role_id
        return bool(role_id == 2)
