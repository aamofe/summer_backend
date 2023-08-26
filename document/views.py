import json
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from jose import ExpiredSignatureError, JWTError
import jwt

from document.models import Document
from summer_backend import settings
from summer_backend.settings import SECRET_KEY
from team.models import Team, Member
from user.authentication import validate_login, validate_all
from user.models import User


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
def share_document(request,team_id):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误！"})
    document_id=request.POST.get('document_id')
    editable=request.POST.get('editable')
    try :
        document=Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    if not isinstance(editable, bool):
        return JsonResponse({'errno': 1, 'msg': "编辑权限错误"})
    if not document.url:
        payload = {"document_id":document_id,"editable":True}
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        document.url_editable=token
        payload = {"document_id":document_id,"editable":False}
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        document.url=token
        document.save()
    data=[document.url_editable if editable else document.url]
    return JsonResponse({'errno':0,'data':data})
def save_document(request,team_id):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误！"})
    document_id=request.POST.get('document_id')
    content=request.POST.get('content')
    try :
        document=Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    document.content=content
    document.save()
    return JsonResponse({'errno': 0, 'msg': "文档内容已保存"})
@validate_all
def view_document(request,token):
    if request.method!='GET':
        return JsonResponse({'errno': 1, 'msg': "请求方式错误"})
    if token.isdigit():
        document_id=token
        editable=True
    else:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        document_id=payload.get('document_id')
        editable=payload.get('editable')
    try:
        document=Document.objects.get(id=document_id,is_deleted=False)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    if editable:
        token = request.META.get('HTTP_Authorization'.upper())
        if not token:
            return redirect('http://www.aamofe.top/api/user/register/')
        token = token.replace('Bearer ', '')
        try:
            jwt_token = jwt.decode(token, settings.SECRET_KEY, options={'verify_signature': False})
        except ExpiredSignatureError:
            return JsonResponse({'errno': 401, 'msg': "登录已过期，请重新登录"})
        except JWTError:
            return JsonResponse({'errno': 401, 'msg': "用户未登录，请先登录"})
        try:
            user = User.objects.get(id=jwt_token.get('id'),isActive=True)
        except User.DoesNotExist:
            return JsonResponse({'errno': 401, 'msg': "用户不存在，请先注册"})
    dict=document.to_dict()
    dict['editable']=editable
    return JsonResponse({'errno': 0, 'msg': "查看成功",'document':dict})


def change_lock(request,team_id):
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
    try :
         document=Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    document.is_locked^=1
    document.save()
    data=[]
    data.append(document.to_dict())
    return JsonResponse({'errno': 0, 'data':data,'msg': "文档上锁状态修改成功"})
