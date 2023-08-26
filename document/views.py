import json
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from document.models import Document
from team.models import Team, Member
from user.authentication import validate_login, validate_all


@validate_login
# Create your views here.
def create_document(request,team_id):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误！"})
    user=request.user
    title=request.POST.get("title")
    content=request.POST.get("content")
    if content is None:
        return JsonResponse({'errno': 1, 'msg': "内容为空"})
    if title is None:
        return JsonResponse({'errno': 1, 'msg': "标题为空"})
    team_list = Team.objects.filter(id=team_id)
    if not team_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    team = team_list[0]
    try:
        member=Member.objects.filter(team=team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    document=Document.objects.create(title=title,content=content,team=team,user=user)
    return JsonResponse({'errno': 0, 'msg': "创建成功"})

@validate_login
def view_document(request,team_id):
    if request.method!='GET':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误"})
    user=request.user
    document_id=request.GET.get("document_id")
    if team_id is None:
        return JsonResponse({'errno': 1, 'msg': "团队id不能为空"})
    team_list = Team.objects.filter(id=team_id)
    if not team_list.exists():
        return JsonResponse({'errno': 1, 'msg': "该团队不存在"})
    team = team_list[0]
    try:
        member=Member.objects.filter(team=team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    document=Document.objects.get(id=document_id)
    data=[]
    data.append(document.to_dict())
    return JsonResponse({'errno': 0, 'msg': "查看成功",'data':data})

# def share_document(request):
