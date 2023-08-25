from django.shortcuts import render
from django.shortcuts import render

# Create your views here.
import json
import os.path
import pprint
import time
import uuid
import platform

import jwt
from django.core.mail import EmailMessage
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
import re
from datetime import datetime, timedelta
from django.template import loader
from jose import JWTError
from jwt import ExpiredSignatureError

from summer_backend.settings import SECRET_KEY, EMAIL_HOST_USER
from user.authentication import validate_all, validate_login
from user.cos_utils import get_cos_client, Label, Category, SubLabel
from user.models import User
from team.models import Team, Member, Project
from django.utils import timezone

# Create your views here.
@validate_login
def create_team(request):
    if request.method == 'POST':
        user = request.user
        team_name = request.POST.get("team_name")
        team = Team.objects.create(name=team_name, user=user)
        member=Member.objects.create(role='CR',user=user,team=team)
        return JsonResponse({'errno': 0, 'msg': "创建团队成功"})
    else :
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
# 邀请好友
@validate_login
def get_invitation(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    team_id=request.GET.get("team_id")
    team_list = Team.objects.filter(id=team_id)
    if not team_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    team=team_list[0]
    member_list=Member.objects.filter(user=user, team=team)
    if not member_list.exists():
        return JsonResponse({'errno': 1, 'msg': "当前用户不属于该团队"})
    member = member_list[0]
    if member.role == 'MB':
        return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
    invitation = team.invitation
    if not invitation:
        payload = {"team_id": team_id}
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        if platform.system()=='linux':
            invitation = "http://www.aamofe.top/api/user/accept/" + token+'/'
        else :
            invitation = "http://127.0.0.1/api/user/accept/" + token+'/'
        team.invitation = invitation
        team.save()
    return JsonResponse({'errno': 1, 'msg': "链接已生成", 'invatation': invitation})


@validate_login
def accept_invitation(request, token):
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    team_id = payload.get('team_id')
    team_list = Team.objects.filter(id=team_id)
    if not team_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    team = team_list[0]
    user = request.user
    member = Member.objects.filter(user=user, team=team)
    if member.exists():
        return JsonResponse({'errno': 1, 'msg': "您已加入该团队"})
    member = Member.objects.create(user=user, team=team)
    return JsonResponse({'errno': 0, 'msg': "加入成功"})

# 获取所有团队

@validate_login
def get_teams(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    member_list = Member.objects.filter(user=user)
    data = []
    for member in member_list:
        team_info = member.team.to_dict()
        team_info['role'] = member.role
        data.append(team_info)
    return JsonResponse({'errno': 0, 'msg': "获取团队", 'data': data})


@validate_login
def get_members(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    team_id=request.GET.get("team_id")
    team_list = Team.objects.filter(id=team_id)
    if not team_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    team = team_list[0]
    member_list = Member.objects.filter(user=user, team=team)
    if not member_list.exists():
        return JsonResponse({'errno': 1, 'msg': "当前用户不属于该团队"})
    member_list = Member.objects.filter(team=team)
    data = []
    for member in member_list:
        user_info = member.user.to_dict()
        user_info['role'] = member.role
        data.append(user_info)
    return JsonResponse({'errno': 0, 'msg': "获取成员", 'data': data})


@validate_login
def update_permisson(request, team_id):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    choice = request.POST.get('choice')  #  MG MB DE
    user_id = request.POST.get('user_id')
    editor = request.user
    team_list = Team.objects.filter(id=team_id)
    if not team_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    team = team_list[0]
    member_list = Member.objects.filter(user=editor, team=team)
    if not member_list.exists():
        return JsonResponse({'errno': 1, 'msg': "当前用户不属于该团队"})
    medtor = member_list[0]
    try:
        edited = User.objects.filter(id=user_id)[0]
    except User.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "该用户不存在"})
    member_list = Member.objects.filter(user=edited, team=team)
    if not member_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该用户不属于该团队"})
    medted = member_list[0]
    if medtor.role == 'MB' or (medtor.role == 'MG' and medted.role == 'CR'):
        return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
    if choice == medted.role:
        return JsonResponse({'errno': 1, 'msg': "身份未发生改变"})
    elif choice == 'DE':
        medted.delete()
    elif choice=='MG'or choice=='MB':
        medted.role = choice
        medted.save()
    else:
        return JsonResponse({'errno': 1, 'msg': "操作错误"})
    return JsonResponse({'errno': 0, 'msg': "操作成功"})

@validate_login
def create(request, team_id):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    project_name = request.POST.get('project_name')
    if not project_name:
        return JsonResponse({'errno': 1, 'msg': "请输入项目名称"})
    team_list = Team.objects.filter(id=team_id)
    if not team_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    team = team_list[0]
    project = Project.objects.create(name=project_name, team=team)
    return JsonResponse({'errno': 1, 'msg': "团队创建成功"})


@validate_login
def update(request, project_id):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    try:
        project = Project.objects.filter(id=project_id)[0]
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    user = request.user
    member_list = Member.objects.filter(user=user, team=project.team)
    if not member_list.exists():
        return JsonResponse({'errno': 1, 'msg': "当前用户不属于该团队"})
    project.is_deleted ^= True
    project.save()
    return JsonResponse({'errno': 0, 'msg': "项目删除成功"})


@validate_login
def rename(request, project_id):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    try:
        project = Project.objects.filter(id=project_id)[0]
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    user = request.user
    new_name = request.POST.get("new_name")
    member_list = Member.objects.filter(user=user, team=project.team)
    if not member_list.exists():
        return JsonResponse({'errno': 1, 'msg': "当前用户不属于该团队"})
    project.name = new_name
    project.save()
    return JsonResponse({'errno': 0, 'msg': "项目删除成功"})