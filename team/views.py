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
from document.models import Document, Prototype

from summer_backend import settings
from summer_backend.settings import SECRET_KEY, EMAIL_HOST_USER
from user.authentication import validate_all, validate_login
from user.cos_utils import get_cos_client, Label, Category, SubLabel
from user.models import User
from team.models import Team, Member, Project
from django.utils import timezone

from user.views import upload_cover_method


# Create your views here.
@validate_login
def create_team(request):
    if request.method == 'POST':
        user = request.user
        team_name = request.POST.get("team_name")
        description = request.POST.get('description')
        if not team_name:
            team_name="未命名团队"
        elif team_name=='个人空间':
            return JsonResponse({'errno':1,'msg':"团队名称不能为个人空间"})
        team = Team.objects.create(name=team_name, user=user)
        cover = request.FILES.get('cover')
        if description:
            team.description = description
        if cover:
            res, cover_url, content = upload_cover_method(cover, user.id, 'team_cover')
            if res == -2:
                return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
            elif res == 1:
                return JsonResponse({'errno': 1, 'msg': content})
            else:
                team.cover_url = cover_url
        team.save()
        member = Member.objects.create(role='CR', user=user, team=team)
        return JsonResponse({'errno': 0, 'msg': "创建团队成功"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})


@validate_login
def update_team(request, team_id):  # 修改团队描述 上传头像
    if request.method == 'POST':
        user = request.user
        description = request.POST.get('description')
        team_name = request.POST.get('team_name')
        cover = request.FILES.get('cover')
        try:
            team=Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
        if not team.user == user:
            return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
        if team_name and team_name!='个人空间':
            team.name = team_name
        if description:
            team.description = description
        if cover:
            res, cover_url, content = upload_cover_method(cover, team.id, 'team_cover')
            if res == -2:
                return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
            elif res == 1:
                return JsonResponse({'errno': 1, 'msg': content})
            else:
                team.cover_url = cover_url
        team.save()
        return JsonResponse({'errno': 0, 'msg': "修改信息成功"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})


# 邀请好友
@validate_login
def get_invitation(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    team_id = request.GET.get("team_id")
    if not team_id:
        return JsonResponse({'errno': 1, 'msg': "请输入team_id"})
    try:
        team=Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    try:
        member=Member.objects.get(team=team,user=user)
    except Member.DoesNotExist:
        print("team_user : ",team.user.id,"当前用户 ： ",user.id)
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if member.role == 'MB':
        return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
    if team.name=='个人空间':
        return JsonResponse({'errno': 1, 'msg': "个人空间不可邀请好友"})
    payload = {"team_id": team_id,'inviter':user.nickname}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    invitation = "http://www.aamofe.top/team/" + token + '/'
    # team.invitation = invitation
    # team.save()
    return JsonResponse({'errno': 0, 'msg': "链接已生成", 'invatation': invitation})

def team_name(request,token):
    if request.method!="GET":
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    team_id = payload.get('team_id')
    inviter=payload.get('inviter')
    if not team_id or not inviter:
        return JsonResponse({'errno': 1, 'msg': "信息解析失败"})
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "团队不存在"})
    invite_info={'inviter':inviter,'team_name':team.name}
    return JsonResponse({"errno":0,'invite_info':invite_info,'msg':'解析团队信息成功'})
@validate_login
def accept_invitation(request,token):
    if request.method!="POST":
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    team_id = payload.get('team_id')
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "团队不存在"})
    user=request.user
    try:
        member=Member.objects.get(team=team,user=user)
        return JsonResponse({'errno': 0, 'msg': "您已加入该团队"})
    except Member.DoesNotExist:
        member = Member.objects.create(user=user, team=team)
        return JsonResponse({'errno': 0, 'msg': "加入成功"})
@validate_login
def all_teams(request):
    print(1)
    if request.method != 'GET':
        print(2)
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    print(3)
    user = request.user
    # print('user_id : ',user.id)
    try:
        user=User.objects.get(id=user.id,is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户id不存在"})
    member_list = Member.objects.filter(user=user)
    # print(4)
    teams = []
    for member in member_list:
        team_info = member.team.to_dict()
        team_info['role'] = member.get_role_display()
        teams.append(team_info)
    teams.append({'team_num':member_list.count()})
    return JsonResponse({'errno': 0, 'msg': "获取团队", 'teams': teams})


@validate_login
def all_members(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    team_id = user.current_team_id
    if not team_id:
        return JsonResponse({'errno': 1, 'msg': "请输入团队id"})
    try:
        team=Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    try:
        member=Member.objects.get(team=team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "当前用户不属于该团队"})
    members = []
    member_list = Member.objects.filter(team=team,role="CR")
    for member in member_list:
        user_info = member.user.to_dict()
        user_info['role'] = member.get_role_display()
        user_info['op']=''
        user_info['role_string']=member.role
        members.append(user_info)
    member_list = Member.objects.filter(team=team,role="MG")
    for member in member_list:
        user_info = member.user.to_dict()
        user_info['role'] = member.get_role_display()
        user_info['op']=''
        user_info['role_string']=member.role
        members.append(user_info)
    member_list = Member.objects.filter(team=team,role="MB")
    for member in member_list:
        user_info = member.user.to_dict()
        user_info['role'] = member.get_role_display()
        user_info['op']=''
        user_info['role_string']=member.role
        members.append(user_info)
    return JsonResponse({'errno': 0, 'msg': "获取成员", 'members': members})


@validate_login
def update_permisson(request, team_id):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    choice = request.POST.get('choice')  # MG MB DE
    user_id = request.POST.get('user_id')
    editor = request.user
    try:
        team=Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    try:
        medtor=Member.objects.get(team=team,user=editor)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    try:
        edited = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "该用户不存在"})
    try:
        medted=Member.objects.get(team=team,user=edited)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if edited.id == editor.id:
        return JsonResponse({'errno': 1, 'msg': "无法修改自身权限"})
    if medtor.role == 'MB' or (medtor.role == 'MG' and medted.role == 'CR'):
        return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
    if choice == medted.role:
        return JsonResponse({'errno': 0, 'msg': "身份未发生改变"})
    elif choice == 'DE':
        medted.delete()
    elif choice == 'MG' or choice == 'MB':
        medted.role = choice
        medted.save()
    else:
        return JsonResponse({'errno': 1, 'msg': "操作错误"})
    return JsonResponse({'errno': 0, 'msg': "操作成功"})


@validate_login
def create_project(request, team_id):
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
    project = Project.objects.create(name=project_name, team=team,user=user)
    return JsonResponse({'errno': 0,'project':project.to_dict(), 'msg': "项目创建成功"})


@validate_login
def delete_one_project(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    project_id=request.GET.get('project_id')
    try:
        project = Project.objects.get(id=project_id,is_deleted=False)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    user = request.user
    try:
        member=Member.objects.get(team=project.team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    project.is_deleted = True
    project.save()
    return JsonResponse({'errno': 0, 'msg': "项目删除成功"})
@validate_login
def recover_one_project(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    project_id=request.POST.get('project_id')
    try:
        project=Project.objects.get(id=project_id,is_deleted=True)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member=Member.objects.get(user=user,team=project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于当前团队"})
    project.is_deleted=False
    project.save()
    return JsonResponse({'errno': 0, 'msg': "项目恢复成功"})

@validate_login
def rename_project(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    project_id=request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id,is_deleted=False)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    user = request.user
    new_name = request.POST.get("name")
    try:
        member=Member.objects.get(team=project.team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    project.name = new_name
    project.save()
    return JsonResponse({'errno': 0, 'msg': "项目重命名成功"})
@validate_login
def checkout_team(request):
    if request.method == 'POST':
        user=request.user
        team_id=request.POST.get('team_id')
        try:
            team = Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
        try:
            member = Member.objects.get(user=user, team=team)
        except Member.DoesNotExist:
           return JsonResponse({'errno': 1, 'msg': "当前用户不属于该团队"})
        user.current_team_id=team.id
        user.save()
        team_info={'user_id': user.id,'current_team':user.current_team_id,'team_name':team.name}
        return JsonResponse({ 'current_team':team_info, 'errno': 0, 'msg': "切换成功"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})

    
@validate_login
def get_current_team(request):
    # print("get_current_team : begin")
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    try :
        team=Team.objects.get(id=user.current_team_id)
    except Team.DoesNotExist:
        try:
            team = Team.objects.get(user=user,name="个人空间")
        except Team.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "个人空间不存在"})
        user.current_team_id=team.id
        user.save()
    team_list=team.to_dict()
    team_list['team_num']= Member.objects.filter(user=user).count()
    project_list=Project.objects.filter(team=team)
    team_list['project_num']=project_list.count()
    member_list=Member.objects.filter(team=team)
    team_list['member_num']=member_list.count()
    member=Member.objects.filter(user=user,team=team)[0]
    team_list['role']=member.get_role_display()
    team_list['role_string']=member.role
    # pprint.pprint(team_list)
    return JsonResponse({'errno': 0,'team':team_list, 'msg': "请求成功"})
@validate_login
def all_projects(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    try:
        team=Team.objects.get(id=user.current_team_id)
    except Team.DoesNotExist:
        team=Team.objects.get(user=user,name='个人空间')
        user.current_team_id=team.id
        user.save()
    projects=Project.objects.filter(team=team,is_deleted=False)
    project_list=[]
    for p in projects:
        project_list.append(p.to_dict())
    return JsonResponse({'errno': 0, 'msg': "获取团队所有项目成功",'projects':project_list})
@validate_login
def get_one_team(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    team_id=request.GET.get('team_id')
    try:
        team=Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    try:
        member=Member.objects.get(user=user,team=team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于当前团队"})
    team_list=team.to_dict()
    team_list['team_num']= Member.objects.filter(user=user).count()
    project_list=Project.objects.filter(team=team)
    team_list['project_num']=project_list.count()
    member_list=Member.objects.filter(team=team)
    team_list['member_num']=member_list.count()
    member=Member.objects.filter(user=user,team=team)[0]
    team_list['role']=member.get_role_display()
    return JsonResponse({'errno': 0,'team':team_list, 'msg': "请求成功"})

#退出团队
@validate_login
def quit_team(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    team_id=request.POST.get("team_id")
    try:
        team=Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    try:
        member=Member.objects.get(user=user,team=team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于当前团队"})
    if member.role=='CR' and team.name!='个人空间':
        member_list=Member.objects.get(team=team)
        member_list.delete()
        team.delete()
    else:
        member.delete()
    return JsonResponse({'errno': 0, 'msg': "成功退出团队"})
@validate_login
def all_deleted_project(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    try:
        team=Team.objects.get(id=user.current_team_id)
    except Team.DoesNotExist:
        team=Team.objects.get(user=user,name='个人空间')
        user.current_team_id=team.id
        user.save()
    projects=Project.objects.filter(team=team,is_deleted=True)
    project_list=[]
    for p in projects:
        project_list.append(p.to_dict())
    return JsonResponse({'errno': 0, 'msg': "获取回收站项目成功",'projects':project_list})

@validate_login
def recover_all_project(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    team_id=request.POST.get('team_id')
    try:
        team=Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "团队不存在"})
    project_list=Project.objects.filter(team=team,is_deleted=True)
    project_list.update(is_deleted=False)
    return JsonResponse({'errno': 0, 'msg': "一键恢复成功"})
@validate_login
def get_one_project(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    project_id=request.GET.get('project_id')
    try:
        project=Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    project_=project.to_dict()
    project_['document_num']=Document.objects.filter(project=project).count()
    project_['prototype_num']=Prototype.objects.filter(project=project).count()
    return JsonResponse({'errno': 0, 'project':project_,'msg': "单个项目信息"})