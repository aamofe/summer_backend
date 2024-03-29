from copy import deepcopy

from django.db.models import Q, Count
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
from document.models import Document, Prototype, Folder

from summer_backend import settings
from summer_backend.settings import SECRET_KEY, EMAIL_HOST_USER
from team.photo import generate_cover
from user.authentication import validate_all, validate_login
from user.cos_utils import get_cos_client, Label, Category, SubLabel
from user.models import User
from team.models import Team, Member, Project
from chat.models import Group, ChatMember
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
        group = Group.objects.create(name=team_name, user=user,actual_team=team.id,type='team')
        cover = request.FILES.get('cover')
        if description:
            team.description = description
            group.description=description
        if cover:
            res, cover_url= upload_cover_method(cover, user.id, 'team_cover')
            if res == -1:
                return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
            else:
                team.cover_url = cover_url
                group.cover_url=cover_url
        else:
            cover_url=generate_cover(2,team.name,team.id)
            team.cover_url = cover_url
            group.cover_url = cover_url
        team.save()
        group.save()
        member = Member.objects.create(role='CR', user=user, team=team)
        chat_member=ChatMember.objects.create(role='CR',user=user,team=group)
        return JsonResponse({'errno': 0, 'team':team.to_dict(),'msg': "创建团队成功"})
    else:
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})


@validate_login
def update_team(request):  # 修改团队描述 上传头像
    if request.method == 'POST':
        user = request.user
        description = request.POST.get('description')
        team_name = request.POST.get('team_name')
        cover = request.FILES.get('cover')
        team_id=user.current_team_id
        try:
            team=Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
        try:
            group=Group.objects.get(actual_team=team_id)
        except Group.DoesNotExist:
            group=Group.objects.create(name=team.name, user=team.user,actual_team=team.id,type='team')
        if not team.user == user:
            return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
        if team.name=='个人空间' or team_name=='个人空间':
            return JsonResponse({'errno': 1, 'msg': "个人空间不能修改名称"})
        if cover:
            res, cover_url= upload_cover_method(cover, team.id, 'team_cover')
            if res == -1:
                return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
            else:
                team.cover_url = cover_url
                group.cover_url=cover_url
        if team_name and team_name!='个人空间':
            old_name=team.name
            new_name=team_name
            team.name = team_name
            if 'random' in str(team.cover_url) and not old_name[0]==new_name[0]:
                cover_url = generate_cover(2, team_name, team.id)
                team.cover_url = cover_url
                group.cover_url = cover_url
            group.name=team_name
        if description:
            team.description = description
            group.description=description
        team.save()
        group.save()
        return JsonResponse({'errno': 0, 'msg': "修改信息成功",'team':team.to_dict()})
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
        group=Group.objects.get(actual_team=team_id)
    except Group.DoesNotExist:
        group=Group.objects.create(name=team.name, user=team.user,actual_team=team.id,type='team')
    try:
        member=Member.objects.get(team=team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    try:
        ChatMember.objects.get(team=group,user=user)
    except ChatMember.DoesNotExist:
        ChatMember.objects.create(role='CR',user=team.user,team=group)  
    if member.role == 'MB':
        return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
    if team.name=='个人空间':
        return JsonResponse({'errno': 1, 'msg': "个人空间不可邀请好友"})
    if not user.nickname :
        return JsonResponse({'errno': 1, 'msg': "用户未设置昵称"})
    payload = {"team_id": team_id,'inviter':user.nickname}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return JsonResponse({'errno': 0, 'msg': "链接已生成", 'token': token})

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
    print('啊啊啊啊接收邀请')
    if request.method!="POST":
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    team_id = payload.get('team_id')
    print('team_id : ',team_id)
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "团队不存在"})
    try:
        group = Group.objects.get(actual_team=team_id)
    except Group.DoesNotExist:
        group=Group.objects.create(name=team.name, user=team.user,actual_team=team.id,type='team')
    user=request.user
    try:
        print('已加入')
        member=Member.objects.get(team=team,user=user)
        print('已加入')
        try:
            chat_member=ChatMember.objects.get(team=group,user=user)
        except ChatMember.DoesNotExist:
            chat_member=ChatMember.objects.create(user=user,team=group)
        print('已加入')
        return JsonResponse({'errno': 0, 'msg': "您已加入该团队"})
    except Member.DoesNotExist:
        print("加入成功！")
        member = Member.objects.create(user=user, team=team)
        chat_member=ChatMember.objects.create(user=user,team=group)
        return JsonResponse({'errno': 0, 'msg': "加入成功"})
@validate_login
def all_teams(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    try:
        user=User.objects.get(id=user.id,is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户id不存在"})
    member_list = Member.objects.filter(user=user)
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
        group=Group.objects.get(actual_team=team_id)
    except Group.DoesNotExist:
        group=Group.objects.create(name=team.name, user=team.user,actual_team=team.id,type='team')
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
    try:
        Medted=ChatMember.objects.get(team=group,user=edited)
    except ChatMember.DoesNotExist:
        Medted=ChatMember.objects.create(team=group,user=edited)
    if edited.id == editor.id:
        return JsonResponse({'errno': 1, 'msg': "无法修改自身权限"})
    if medtor.role == 'MB' or (medtor.role == 'MG' and medted.role == 'CR'):
        return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
    if choice == medted.role:
        return JsonResponse({'errno': 0, 'msg': "身份未发生改变"})
    elif choice == 'DE':
        medted.delete()
        Medted.delete()
    elif choice == 'MG' or choice == 'MB':
        medted.role = choice
        Medted.role=choice
        medted.save()
        Medted.save()
    else:
        return JsonResponse({'errno': 1, 'msg': "操作错误"})
    return JsonResponse({'errno': 0, 'msg': "操作成功"})


@validate_login
def create_project(request, team_id):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    project_name = request.POST.get('project_name')
    cover=request.FILES.get("cover")
    if not project_name:
        return JsonResponse({'errno': 1, 'msg': "请输入项目名称"})
    team_list = Team.objects.filter(id=team_id)
    if not team_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    team = team_list[0]
    project = Project.objects.create(name=project_name, team=team,user=user)
    folder=Folder.objects.create(name=project_name,project=project,user=user,parent_folder=None)
    if cover:
        res,cover_url=upload_cover_method(cover,project.id,'project_cover')
        if res == -1:
            return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
    else:
        cover_url=generate_cover(1,project_name,project.id)
    project.cover_url = cover_url
    project.save()
    project_info=project.to_dict()
    project_info['folder_id']=folder.id
    project_info['folder_name']=folder.name
    return JsonResponse({'errno': 0,'project':project_info, 'msg': "项目创建成功"})


@validate_login
def delete_one_project(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    project_id=request.POST.get('project_id')
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
    old_name=project.name
    project.name = new_name
    if not old_name[0]==new_name[0]:
        cover_url=generate_cover(1,new_name,project.id)
        project.cover_url=cover_url
    try:
        folder=Folder.objects.get(parent_folder=None,project=project)
        folder.name=new_name
        folder.save()
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
    project.save()
    return JsonResponse({'errno': 0, 'msg': "项目重命名成功",'project':project.to_dict()})
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
    return JsonResponse({'errno': 0,'team':team_list, 'msg': "请求成功"})

@validate_login
def all_projects(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    team_id = user.current_team_id  # 选择特定团队的项目
    sort_by = request.GET.get('sort_by', '-created_at')  # 默认按创建时间降序排序
    try:
        team = Team.objects.get(id=team_id)
    except Team.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "团队不存在"})
    try:
        member = Member.objects.get(user=user, team=team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    valid_sort_fields = ['created_at', 'name']
    if sort_by.startswith('-'):
        sort_field = sort_by[1:]
        if sort_field not in valid_sort_fields:
            sort_field = 'created_at'  # 默认排序字段为 created_at
        sort_field = '-' + sort_field
    else:
        sort_field = sort_by if sort_by in valid_sort_fields else '-created_at'
    project_list = Project.objects.filter(team=team,is_deleted=False).order_by(sort_field)
    projects=[]
    for p in project_list:
        try:
            folder=Folder.objects.get(parent_folder=None,project=p)
        except Folder.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "项目无父文件夹"})
        pp=p.to_dict()
        pp['folder_id']=folder.id
        projects.append(pp)
    return JsonResponse({'errno': 0, 'projects': projects, 'msg': "获取项目列表成功"})


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
        group=Group.objects.get(actual_team=team_id)
    except Group.DoesNotExist:
        group=Group.objects.create(name=team.name, user=team.user,actual_team=team.id,type='team')
    try:
        member=Member.objects.get(user=user,team=team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于当前团队"})
    if member.role=='CR' and team.name!='个人空间':
        member_list=Member.objects.get(team=team)
        member_list.delete()
        team.delete()
        chat_member_list=ChatMember.objects.filter(team=group)
        chat_member_list.delete()
        group.delete()
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
    project_['document_num']=Document.objects.filter(parent_folder__project=project).count()
    project_['prototype_num']=Prototype.objects.filter(parent_folder__project=project).count()
    try:
        folder=Folder.objects.get(parent_folder=None,project=project)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1 ,'msg': "父文件夹不存在"})
    project_['folder_id']=folder.id
    return JsonResponse({'errno': 0, 'project':project_,'msg': "单个项目信息"})

@validate_login
def search(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    query=request.POST.get('query')
    teams=[]
    projects=[]
    prototypes=[]
    if query:
        teams = Team.objects.filter(Q(member__user=user,name__icontains=query) | Q(description__icontains=query))
        teams = teams.order_by('-created_at')  # 按创建时间降序排序
        projects=Project.objects.filter(Q(project__team__member__user=user) | Q(description__icontains=query))
        projects=projects.order_by('-created_at')
        prototypes = Project.objects.filter(Q(prototype__team__member__user=user) | Q(description__icontains=query))
        prototypes=prototypes.order_by('-created_at')
    team_list=[team.to_dict() for team in teams]
    project_list=[project.to_dict() for project in projects]
    prototype_list=[ prototype.to_dict() for  prototype in  prototypes]
    return JsonResponse({'errno':0,'teams':team_list,' prototypes': prototype_list,'project':project_list,'msg':'查询成功'})

@validate_login
def copy(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    
    user = request.user
    project_id = request.POST.get('project_id')
    
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    
    project1 = deepcopy(project)
    project1.id = None
    project1.name = f"{project.name} (Copy)"  # 修改名称，以免重名
    project1.save()

    url=generate_cover(1,project1.name,project1.id)
    project1.cover_url=url
    project1.save()
    try:
        folder = Folder.objects.get(parent_folder=None, project=project)
    except Folder.DoesNotExist:
         return JsonResponse({'errno': 1, 'msg': '数据库bug'})
    
    folder1 = deepcopy(folder)
    folder1.project = project1
    folder1.parent_folder = None  # 更新为新项目的根文件夹
    folder1.id = None
    folder1.name=project1.name
    folder1.save()
    
    for f in Folder.objects.filter(parent_folder=folder):
        f1 = deepcopy(f)
        f1.project = project1
        f1.parent_folder = folder1
        f1.id = None
        f1.save()
        
        for d in Document.objects.filter(parent_folder=f):
            d1 = deepcopy(d)
            d1.project = project1
            d1.parent_folder = f1
            d1.id = None
            d1.save()
        
        for p in Prototype.objects.filter(parent_folder=f):
            p1 = deepcopy(p)
            p1.project = project1
            p1.parent_folder = f1
            p1.id = None
            p1.save()
    
    for d in Document.objects.filter(parent_folder=folder):
        d1 = deepcopy(d)
        d1.project = project1
        d1.parent_folder = folder1
        d1.id = None
        d1.save()
    
    for p in Prototype.objects.filter(parent_folder=folder):
        p1 = deepcopy(p)
        p1.project = project1
        p1.parent_folder = folder1
        p1.id = None
        p1.save()
    projects=project1.to_dict()
    projects['folder']=folder1.id
    return JsonResponse({
        'errno': 0,
        'msg': '复制成功',
        'project':projects,
    })

@validate_login
def delete_permanently(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    project_id=request.POST.get('project_id')
    if not project_id:
        return JsonResponse({'errno': 1, 'msg': "请输入项目id"})
    elif  project_id=='0':
        team_id=user.current_team_id
        try:
            team=Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "当前团队不存在"})
        projects=Project.objects.filter(team=team,is_deleted=True)
        projects.delete()
        return JsonResponse({'errno': 0, 'msg': "所有项目已删除"})
    else:
        try:
            project=Project.objects.get(id=project_id,is_deleted=True)
        except Project.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "项目未删除"})
        project.delete()
        return JsonResponse({'errno': 0, 'msg': "项目已删除"})