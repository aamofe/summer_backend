import json
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from jose import ExpiredSignatureError, JWTError
import jwt
from django.contrib.auth.models import AnonymousUser
from document.models import Document, Prototype
from summer_backend import settings
from summer_backend.settings import SECRET_KEY
from team.models import Team, Member, Project
from user.authentication import validate_login, validate_all
from user.models import User


@validate_login
# Create your views here.
def create_document(request,project_id):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    user=request.user
    title=request.POST.get("title")
    content=request.POST.get("content")
    # if content is None:
    #     return JsonResponse({'errno': 1, 'msg': "内容为空"})
    if title is None:
        return JsonResponse({'errno': 1, 'msg': "标题为空"})
    # try:
    #     team=Team.objects.get(id=user.current_team_id)
    # except Team.DoesNotExist:
    #     return JsonResponse({'errno': 1, 'msg': "当前团队不存在"})
    try:
        project=Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member=Member.objects.filter(team=project.team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    document=Document.objects.create(title=title,project=project,user=user)
    if content:
        document.content=content
        document.save()
    return JsonResponse({'errno': 0,"document":document.to_dict(), 'msg': "创建成功"})
def share_document(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    document_id=request.POST.get('document_id')
    editable=request.POST.get('editable')
    try :
        document=Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    print("editable : ",editable)
    try:
        editable = int(editable)  # 将字符串转换为整数
    except (ValueError, TypeError):
        return JsonResponse({'errno': 1, 'msg': "编辑权限错误"})
    if editable != 1 and editable != 0:
        return JsonResponse({'errno': 1, 'msg': "编辑权限错误"})
    if not document.url:
        payload = {"document_id":document_id,"editable":True}
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        document.url_editable="http://www.aamoef.top/tiptap/"+token+'/'
        payload = {"document_id":document_id,"editable":False}
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        document.url="http://www.aamoef.top/tiptap/"+token+'/'
        document.save()
    data=[document.url_editable if editable else document.url]
    return JsonResponse({'errno':0,'data':data})
def save_document(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    document_id=request.POST.get('document_id')
    content=request.POST.get('content')
    title=request.POST.get('title')
    try :
        document=Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    if title:
        document.title=title
    if content:
        document.content=content
    document.save()
    return JsonResponse({'errno': 0, 'msg': "文档内容已保存"})
@validate_all
def view_document(request,token):
    print(1)
    if request.method!='GET':
        print(2)
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    if token.isdigit():
        document_id=token
        try:
            document=Document.objects.get(id=document_id,is_deleted=False)
        except Document.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文档不存在"})
        team_id=document.project.team.id
        try :
            team=Team.objects.get(id=team_id)
        except Team.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "团队不存在"})
        user=request.user
        if isinstance(user, AnonymousUser):
            editable=False
        else:
            try:
                member=Member.objects.get(user=user,team=team)
                editable=True
            except Member.DoesNotExist:
                editable=False
    else:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        document_id=payload.get('document_id')
        try:
            document=Document.objects.get(id=document_id,is_deleted=False)
        except Document.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文档不存在"})
        editable=payload.get('editable')
    dict=document.to_dict()
    dict['editable']=editable
    return JsonResponse({'errno': 0, 'msg': "查看成功",'document':dict})

@validate_all
def change_lock(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    document_id=request.POST.get("document_id")
    type=request.POST.get('type')# + -
    try :
        document=Document.objects.get(id=document_id)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    if type=='+':
        document.is_locked+=1
    elif type=='-':
        if document.is_locked==0:
            return JsonResponse({'errno': 1, 'msg': "锁为0，不可再减"})
        document.is_locked-=1
    else:
        return JsonResponse({'errno': 1, 'msg': "操作符号错误"})
    document.save()
    return JsonResponse({'errno': 0, 'document':document.to_dict(),'msg': "文档上锁状态修改成功"})
@validate_login
def all_documents(request,project_id):
    if request.method!='GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member=Member.objects.get(user=user,team=project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    document_list=Document.objects.filter(project=project)
    documents=[]
    for d in document_list:
        documents.append(d.to_dict())
    documents.append({'document_num':document_list.count()})
    return JsonResponse({'errno': 0,'documents':documents, 'msg': "获取原型成功"})

@validate_login
def create_prototype(request,project_id):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    # try :
    #     team=Team.objects.get(id=team_id,is_deleted=False)
    # except Team.DoesNotExist:
    #     return JsonResponse({'errno': 1, 'msg': "团队不存在"})
    try:
        project=Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    title=request.POST.get('title')
    content=request.POST.get('content')
    try:
        member=Member.objects.filter(team=project.team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if title:
        prototype=Prototype.objects.create(title=title,project=project,user=user)
    else:
        return JsonResponse({'errno': 1, 'msg': "请输入标题"})
    if content:
        prototype.conten=content
    prototype.save()
    return JsonResponse({'errno':0,"prototype":prototype.to_dict(),'msg':'原型创建成功'})
@validate_login
def save_prototype(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    prototype_id=request.POST.get('prototype_id')
    try :
        prototype=Prototype.objects.get(id=prototype_id,is_deleted=False)
    except Prototype.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "原型不存在"})
    try:
        member=Member.objects.get(user=user,team=prototype.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    content = request.POST.get('content')
    title = request.POST.get('title')
    if title:
        prototype.title=title
    if content:
        prototype.content=content
    else:
        return JsonResponse({'errno': 1, 'msg': "请上传修改内容"})
    prototype.save()
    return JsonResponse({'errno': 0, 'msg': "原型保存成功"})

#获取单个原型
@validate_login
def view_prototype(request):
    if request.method!='GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    prototype_id=request.GET.get('prototype_id')
    print("111 ",prototype_id)
    try:
        prototype=Prototype.objects.get(id=prototype_id)
    except Prototype.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "原型不存在"})
    try:
        member=Member.objects.get(user=user,team=prototype.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    return JsonResponse({'errno': 0,'prototype':prototype.to_dict(), 'msg': "获取原型成功"})
#当前项目所有原型
def all_prototype(request,project_id):
    if request.method!='GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    prototype_list=Prototype.objects.filter(project=project)
    prototype=[]
    for p in prototype_list:
        prototype.append(p.to_dict())
    prototype.append({'prototype_num':prototype_list.count()})
    return JsonResponse({'errno': 0,'prototype':prototype, 'msg': "获取原型成功"})

@validate_login
def all_deleted_document(request):  # 包括 原型和协作文档
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    project_id=request.GET.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    document_list=Document.objects.filter(project=project,is_deleted=True)
    prototype_list=Prototype.objects.filter(project=project,is_deleted=True)
    documents=[]
    projects=[]
    for d in document_list:
        documents.append(d.to_dict())
    for p in prototype_list:
        projects.append(p.to_dict())
    return JsonResponse({'errno': 0, 'msg': "获取回收站项目成功", 'documents':documents,'projects':documents})

@validate_login
def recover_one_document(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    prototype_id=request.POST.get('prototype_id')
    document_id=request.POST.get('document_id')
    if prototype_id:
        try:
            prototype=Prototype.objects.get(id=prototype_id,is_deleted=True)
        except Prototype.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "原型不存在"})
        prototype.is_deleted=False
        prototype.save()
    if document_id:
        try:
            document=Prototype.objects.get(id=document_id,is_deleted=True)
        except Document.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文档不存在"})
        # document.update()
        document.is_deleted=False
        document.save()
    return JsonResponse({'errno': 0, 'msg': "恢复单个文档成功"})

@validate_login
def recover_all_document(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    project_id=request.POST.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    document_list = Document.objects.filter(project=project, is_deleted=True)
    prototype_list = Prototype.objects.filter(project=project, is_deleted=True)
    document_list.update(is_deleted=False)
    prototype_list.update(is_deleted=False)
    return JsonResponse({'errno': 0, 'msg': "一键恢复成功"})