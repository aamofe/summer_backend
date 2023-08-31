import json

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from jose import ExpiredSignatureError, JWTError
import jwt
from django.contrib.auth.models import AnonymousUser
from document.models import Document, Prototype, History, Folder, Copy
from summer_backend import settings
from summer_backend.settings import SECRET_KEY
from team.models import Team, Member, Project
from user.authentication import validate_login, validate_all
from user.models import User


@validate_login
# Create your views here.
# def create_document(request,project_id):
#     if request.method!='POST':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
#     user=request.user
#     title=request.POST.get("title")
#     content=request.POST.get("content")
#     # if content is None:
#     #     return JsonResponse({'errno': 1, 'msg': "内容为空"})
#     if title is None:
#         return JsonResponse({'errno': 1, 'msg': "标题为空"})
#     # try:
#     #     team=Team.objects.get(id=user.current_team_id)
#     # except Team.DoesNotExist:
#     #     return JsonResponse({'errno': 1, 'msg': "当前团队不存在"})
#     try:
#         project=Project.objects.get(id=project_id)
#     except Project.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "项目不存在"})
#     try:
#         member=Member.objects.filter(team=parent_folder.project.team,user=user)
#     except Member.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
#     document=Document.objects.create(title=title,project=project,user=user)
#     if content:
#         document.content=content
#         document.save()
#     return JsonResponse({'errno': 0,"document":document.to_dict(), 'msg': "创建成功"})
def share_document(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    document_id=request.POST.get('document_id')
    editable=request.POST.get('editable')
    try :
        document=Document.objects.get(id=document_id,parent_folder__is_deleted=False)
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
# def save_document(request):
#     if request.method!='POST':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
#     document_id=request.POST.get('document_id')
#     content=request.POST.get('content')
#     title=request.POST.get('title')
#     try :
#         document=Document.objects.get(id=document_id)
#     except Document.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "文档不存在"})
#     if title:
#         document.title=title
#     if content:
#         document.content=content
#     document.save()
#     return JsonResponse({'errno': 0, 'msg': "文档内容已保存"})
@validate_all
def view_document(request,token):
    if request.method!='GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    if token.isdigit():
        document_id=token
        try:
            document=Document.objects.get(id=document_id,is_deleted=False,parent_folder__is_deleted=False)
        except Document.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文档不存在"})
        team_id=document.parent_folder.project.team.id
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
            document=Document.objects.get(id=document_id,is_deleted=False,parent_folder__is_deleted=False)
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
        document=Document.objects.get(id=document_id,parent_folder__is_deleted=False)
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
# @validate_login
# def all_documents(request,project_id):
#     if request.method!='GET':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user=request.user
#     try:
#         project = Project.objects.get(id=project_id)
#     except Project.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "项目不存在"})
#     try:
#         member=Member.objects.get(user=user,team=parent_folder.project.team)
#     except Member.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
#     document_list=Document.objects.filter(project=project)
#     documents=[]
#     for d in document_list:
#         documents.append(d.to_dict())
#     documents.append({'document_num':document_list.count()})
#     return JsonResponse({'errno': 0,'documents':documents, 'msg': "获取原型成功"})

# @validate_login
# def create_prototype(request,project_id):
#     if request.method!='POST':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user=request.user
#     try:
#         project=Project.objects.get(id=project_id)
#     except Project.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "项目不存在"})
#     title=request.POST.get('title')
#     content=request.POST.get('content')
#     try:
#         member=Member.objects.filter(team=parent_folder.project.team,user=user)
#     except Member.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
#     if title:
#         prototype=Prototype.objects.create(title=title,project=project,user=user)
#     else:
#         return JsonResponse({'errno': 1, 'msg': "请输入标题"})
#     if content:
#         prototype.conten=content
#     prototype.save()
#     return JsonResponse({'errno':0,"prototype":prototype.to_dict(),'msg':'原型创建成功'})
# @validate_login
# def save_prototype(request):
#     if request.method!='POST':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user=request.user
#     prototype_id=request.POST.get('prototype_id')
#     try :
#         prototype=Prototype.objects.get(id=prototype_id,is_deleted=False)
#     except Prototype.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "原型不存在"})
#     try:
#         member=Member.objects.get(user=user,team=prototype.parent_folder.project.team)
#     except Member.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
#     content = request.POST.get('content')
#     title = request.POST.get('title')
#     if title:
#         prototype.title=title
#     if content:
#         prototype.content=content
#     else:
#         return JsonResponse({'errno': 1, 'msg': "请上传修改内容"})
#     prototype.save()
#     return JsonResponse({'errno': 0, 'msg': "原型保存成功"})

@validate_login
def share_prototype(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    prototype_id=request.POST.get('prototype_id')
    visible=request.POST.get('visible')
    try :
        prototype=Prototype.objects.get(id=prototype_id,is_deleted=False,parent_folder__is_deleted=False)
    except Prototype.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    except (ValueError, TypeError):
        return JsonResponse({'errno': 1, 'msg': "编辑权限错误"})
    token=prototype.token
    if not prototype.token:
        payload = {"prototype_id":prototype_id,}
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
        prototype.token=token
    if visible=='1':
        prototype.visible=True
    elif visible=='0':
        prototype.visible=False
    else:
        return JsonResponse({'errno': 0, 'token': token, 'msg': '操作错误'})
    prototype.save()
    return JsonResponse({'errno':0,'token':token,'msg':'获取预览链接成功'})
#获取单个原型
@validate_login
def view_prototype(request,token):
    if request.method!='GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user=request.user
    if token.isdigit():
        editable=True
        prototype_id=token
        print("当前用户 : ",user.id )
        try:
            prototype = Prototype.objects.get(id=prototype_id, is_deleted=False,parent_folder__is_deleted=False)
        except Prototype.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "原型不存在"})
        try:
            member = Member.objects.get(user=user, team=prototype.parent_folder.project.team)
        except Member.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
        prototypes = prototype.to_dict()
        prototypes['editable'] = editable
    else:
        editable=False
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        prototype_id = payload.get('prototype_id')
        if not prototype_id:
            return JsonResponse({'errno': 1, 'msg': "解密失败"})
        try:
            prototype = Prototype.objects.get(id=prototype_id, is_deleted=False,parent_folder__is_deleted=False)
        except Prototype.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "原型不存在"})
        if not prototype.visible:
            return JsonResponse({'errno': 1, 'msg': "链接已失效"})
        prototype_list=Prototype.objects.filter(parent_folder__project= prototype.parent_folder.project)
        prototypes=[prototype.to_dict() for prototype in prototype_list]
        prototypes.append({'editable':editable})
    return JsonResponse({'errno': 0,'prototype':prototypes, 'msg': "获取原型成功"})
#当前项目所有原型
# def all_prototype(request,project_id):
#     if request.method!='GET':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user=request.user
#     try:
#         project = Project.objects.get(id=project_id)
#     except Project.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "项目不存在"})
#     prototype_list=Prototype.objects.filter(project=project)
#     prototype=[]
#     for p in prototype_list:
#         prototype.append(p.to_dict())
#     prototype.append({'prototype_num':prototype_list.count()})
#     return JsonResponse({'errno': 0,'prototype':prototype, 'msg': "获取原型成功"})

# @validate_login
# def all_deleted_document(request):  # 包括 原型和协作文档
#     if request.method != 'GET':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user = request.user
#     project_id=request.GET.get('project_id')
#     try:
#         project = Project.objects.get(id=project_id)
#     except Project.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "项目不存在"})
#     document_list=Document.objects.filter(project=project,is_deleted=True)
#     prototype_list=Prototype.objects.filter(project=project,is_deleted=True)
#     documents=[]
#     projects=[]
#     for d in document_list:
#         documents.append(d.to_dict())
#     for p in prototype_list:
#         projects.append(p.to_dict())
#     return JsonResponse({'errno': 0, 'msg': "获取回收站项目成功", 'documents':documents,'projects':documents})

# @validate_login
# def restore_one_document(request):
#     if request.method != 'POST':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user = request.user
#     prototype_id=request.POST.get('prototype_id')
#     document_id=request.POST.get('document_id')
#     if prototype_id:
#         try:
#             prototype=Prototype.objects.get(id=prototype_id,is_deleted=True)
#         except Prototype.DoesNotExist:
#             return JsonResponse({'errno': 1, 'msg': "原型不存在"})
#         prototype.is_deleted=False
#         prototype.save()
#     if document_id:
#         try:
#             document=Prototype.objects.get(id=document_id,is_deleted=True)
#         except Document.DoesNotExist:
#             return JsonResponse({'errno': 1, 'msg': "文档不存在"})
#         # document.update()
#         document.is_deleted=False
#         document.save()
#     return JsonResponse({'errno': 0, 'msg': "恢复单个文档成功"})
#
# @validate_login
# def recover_all_document(request):
#     if request.method != 'POST':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user = request.user
#     project_id=request.POST.get('project_id')
#     try:
#         project = Project.objects.get(id=project_id)
#     except Project.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "项目不存在"})
#     document_list = Document.objects.filter(project=project, is_deleted=True)
#     prototype_list = Prototype.objects.filter(project=project, is_deleted=True)
#     document_list.update(is_deleted=False)
#     prototype_list.update(is_deleted=False)
#     return JsonResponse({'errno': 0, 'msg': "一键恢复成功"})


@validate_login
def create(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    file_type = request.POST.get('file_type')  # 原型 文档
    folder_id=request.POST.get('folder_id')

    title = request.POST.get("title")
    content = request.POST.get("content")
    if not title or not file_type or not title or not folder_id :
        return JsonResponse({'errno': 1, 'msg': "参数不全"})
    if not(file_type=='document' or file_type=='prototype'):
        return JsonResponse({'errno': 1, 'msg': "创建文件类型错误"})
    try:
        folder = Folder.objects.get(id=folder_id,is_deleted=False)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
    try:
        member = Member.objects.filter(team=folder.parent_folder.project.team, user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if file_type=='document':
        file = Document.objects.create(title=title,folder=folder, user=user)
    else:
        file = Prototype.objects.create(title=title, folder=folder, user=user)
    if content:
        file.content = content
        file.save()
    return JsonResponse({'errno': 0, "document": file.to_dict(), 'msg': "创建成功"})
@validate_login
def delete(request,):#删除/彻底 一个/多个 文档/原型
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    file_type=request.POST.get('file_type')#原型 文档
    file_id=request.POST.get('file_id') #删除1个 删除所有
    folder_id=request.POST.get('folder_id')
    forerver=request.POST.get('forever')#0代表否 1代表是
    if not file_type or not folder_id or not file_id or not forerver:
        return JsonResponse({'errno': 1, 'msg': "参数不全"})
    if not(file_type=='document' or file_type=='prototype') or not file_id.isdigit() or not forerver in {str(0),str(1)}:
        return JsonResponse({'errno': 1, 'msg': "参数值错误"})
    try:
        folder = Folder.objects.get(id=folder_id,is_deleted=False)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
    try:
        member = Member.objects.get(user=user, team=folder.parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if file_id==0:
        if file_type=='document':
            file_list = Document.objects.filter(folder=folder)
        else:
            file_list = Prototype.objects.filter(folder=folder)
        if forerver=='1':
                file_list.delete()
        else:
            file_list.update(is_deleted=True)
            file_list.update(deleted_at=timezone.now())
        return JsonResponse({'errno': 0, 'msg': "删除成功"})
    else:
        if file_type == 'document':
            try:
                file=Document.objects.get(id=file_id,is_deleted=False,parent_folder__is_deleted=False)
            except Document.DoesNotExist:
                return JsonResponse({'errno': 1, 'msg': "文档不存在"})
        else:
            try:
                file = Prototype.objects.get(id=file_id,is_deleted=False,parent_folder__is_deleted=False)
            except Project.DoesNotExist:
                return JsonResponse({'errno': 1, 'msg': "原型不存在"})
        if forerver=='1':
            file.delete()
            print("彻底")
        else:
            print(file.is_deleted)
            file.is_deleted=True
            file.deleted_at=timezone.now()
            file.save()
            print(file.is_deleted)
        return JsonResponse({'errno': 0, 'msg': "删除成功"})

# @validate_login
# def restore(request):
#     if request.method != 'POST':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user = request.user
#     file_type = request.POST.get('file_type')  # 原型 文档
#     file_id = request.POST.get('file_id')  # 删除1个 删除所有
#     folder_id = request.POST.get('folder_id')
#     # print(file_type,file_id,folder_id)
#     if not file_type or not file_id :
#         return JsonResponse({'errno': 1, 'msg': "参数不全"})
#     if not (file_type == 'document' or file_type == 'prototype') or not file_id.isdigit():
#         return JsonResponse({'errno': 1, 'msg': "参数值错误"})
#     try:
#         folder = Folder.objects.get(id=folder_id,is_deleted=False)
#     except Folder.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
#     try:
#         member = Member.objects.get(user=user, team=folder.parent_folder.project.team)
#     except Member.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
#     if file_id == 0:
#         if file_type == 'document':
#             file_list = Document.objects.filter(folder=folder)
#         else:
#             file_list = Prototype.objects.filter(folder=folder)
#         file_list.update(is_deleted=False)
#         return JsonResponse({'errno': 0, 'msg': "恢复成功"})
#     else:
#         if file_type == 'document':
#             print(file_id)
#             try:
#                 file = Document.objects.get(id=file_id,is_deleted=True,parent_folder__is_deleted=False)
#             except Document.DoesNotExist:
#                 return JsonResponse({'errno': 1, 'msg': "文档不存在"})
#         else:
#             try:
#                 file = Prototype.objects.get(id=file_id,is_deleted=True,parent_folder__is_deleted=False)
#             except:
#                 return JsonResponse({'errno': 1, 'msg': "原型不存在"})
#         print(file.is_deleted)
#         file.is_deleted = False
#         file.save()
#         print(file.is_deleted)
#         return JsonResponse({'errno': 0, 'msg': "恢复成功"})
@validate_login
def save(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    content=request.POST.get('content')
    file_type = request.POST.get('file_type')  # 原型 文档
    file_id = request.POST.get('file_id')  # 删除1个 删除所有
    folder_id = request.POST.get('folder_id')
    title=request.POST.get('title')
    user=request.user
    if not file_type or not file_id or not folder_id:
        return JsonResponse({'errno': 1, 'msg': "参数不全"})
    if not(file_type=='document' or file_type=='prototype') or not file_id.isdigit() or not folder_id.isdigit() :
        return JsonResponse({'errno': 1, 'msg': "参数值错误"})
    try:
        folder =Folder.objects.get(id=folder_id)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member = Member.objects.get(user=user, team=folder.parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if file_type=='document':
        try :
            file=Document.objects.get(id=file_id)
        except Document.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    else:
        try :
            file=Prototype.objects.get(id=file_id,is_deleted=False)
        except Prototype.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "原型不存在"})
    if title:
        file.title=title
    if content:
        file.content=content
    file.save()
    return JsonResponse({'errno': 0, 'msg': "内容已保存"})
# @validate_login
# def all_file(request):
#     if request.method != 'GET':
#         return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
#     user = request.user
#     file_type=request.GET.get("file_type")
#     project_id=request.GET.get(('project_id'))
#     if not file_type or not project_id:
#         return JsonResponse({'errno': 1, 'msg': "参数不全"})
#     if not (file_type == 'document' or file_type == 'prototype') or not project_id.isdigit():
#         return JsonResponse({'errno': 1, 'msg': "参数值错误"})
#     try:
#         project = Project.objects.get(id=project_id)
#     except Project.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "项目不存在"})
#     try:
#         member = Member.objects.get(user=user, team=parent_folder.project.team)
#     except Member.DoesNotExist:
#         return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
#     if file_type=='document':
#         file_list = Document.objects.filter(project=project)
#     else:
#         file_list = Prototype.objects.filter(project=project)
#     files = []
#     for d in file_list:
#         files.append(d.to_dict())
#     files.append({'document_num': file_list.count()})
#     return JsonResponse({'errno': 0, 'files': files, 'msg': "获取原型成功"})
@validate_login
def all_deleted(request):  # 包括 原型和协作文档
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    project_id = request.GET.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    deleted_folders = Folder.objects.filter(project=project, is_deleted=True)
    deleted_documents = Document.objects.filter(Q(folder__project=project, is_deleted=True))
    deleted_prototype = Prototype.objects.filter(Q(folder__project=project, is_deleted=True))
    # Combine and sort the deleted items by deletion time
    deleted_items = list(deleted_folders) + list(deleted_documents)+list(deleted_prototype)
    deleted_items.sort(key=lambda item: item.deleted_at, reverse=True)

    deleted_items_data = []
    for item in deleted_items:
        deleted_items_data.append(item.to_dict())

    return JsonResponse({'errno': 0, 'msg': "获取已删除项目成功", 'deleted_items': deleted_items_data})

@validate_login
def history(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    document_id=request.GET.get('document_id')
    try:
        document = Document.objects.get(id=document_id,is_deleted=False)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    history_list = History.objects.filter(document=document).order_by('-modified_at')[:10]
    history= [history.to_dict() for history in history_list]
    return JsonResponse({'errno': 0,'history':history, 'msg': "历史记录返回成功"})


@validate_login
def create_folder(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    user = request.user
    project_id = request.POST.get('project_id')
    parent_folder_id = request.POST.get('folder_id')  # 修改参数名为 parent_folder_id
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member=Member.objects.get(user=user,team=parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if parent_folder_id:
        try:
            parent_folder = Folder.objects.get(id=parent_folder_id, project=project)
        except Folder.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "父文件夹不存在"})
    else:
        parent_folder = None
    if parent_folder.parent_folder!=None and parent_folder.parent_folder.parent_folder!=None:
        return JsonResponse({'errno': 1, 'msg': "不可创建三级文件夹"})
    folder_name = request.POST.get('folder_name')  # 从请求中获取文件夹名
    if not folder_name:
        return JsonResponse({'errno': 1, 'msg': "文件夹名称不能为空"})
    folder = Folder.objects.create(name=folder_name, project=project, user=user, parent_folder=parent_folder)
    return JsonResponse({'errno': 0, 'msg': "文件夹创建成功", 'folder': folder.to_dict()})


@validate_login
def delete_folder(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    user = request.user
    project_id = request.POST.get('project_id')
    folder_id = request.POST.get('folder_id')
    forever = request.POST.get('forever')  # 新增参数 forever
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member=Member.objects.get(user=user,team=parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    try:
        folder = Folder.objects.get(id=folder_id, project=project)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
    if forever == '1':  # 如果 forever 为 1，永久删除
        # 递归删除子文件夹
        def delete_folder_recursive(folder):
            child_folders = folder.child_folders.all()
            for child_folder in child_folders:
                delete_folder_recursive(child_folder)
            folder.delete()
        delete_folder_recursive(folder)
    else:  # 如果 forever 不为 1，逻辑删除
        # def delete_folder_recursive(folder):
        #     child_folders = folder.child_folders.all()
        #     for child_folder in child_folders:
        #         delete_folder_recursive(child_folder)
        folder.is_deleted = True
        folder.deleted_at=timezone.now()
        folder.save()
        # delete_folder_recursive(folder)
    return JsonResponse({'errno': 0, 'msg': "文件夹删除成功"})

@validate_login
def view_folder(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    project_id = request.GET.get('project_id')
    folder_id = request.GET.get('folder_id')
    user=request.user
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member=Member.objects.get(user=user,team=parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    try:
        folder = Folder.objects.get(id=folder_id, project=project)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
    if folder.is_deleted==True:
        try:
            copy=Copy.objects.get(original=folder)
            folder=copy.revised
        except Copy.DoesNotExist:
            pass
    children = []
    for child_folder in folder.child_folders.all():
        children.append(child_folder.to_dict())  # 递归获取子文件夹信息
    for document in Document.objects.filter(folder=folder):
        children.append(document.to_dict())
    for prototype in Prototype.objects.filter(project=project):
        children.append(prototype.to_dict())

    folder_info = folder.to_dict()
    folder_info['children'] = children
    return JsonResponse({'errno': 0, 'msg': "获取文件夹信息成功", 'folder': folder_info})

@validate_login
def restore(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})

    user = request.user
    project_id = request.POST.get('project_id')
    file_id = request.POST.get('file_id')  # ID of the item to be restored
    file_type= request.POST.get('file_type')
    if not file_type in{'folder','document','prototype'} or not file_id or not project_id:
        return JsonResponse({'errno': 1, 'msg': "参数不正确"})
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    if file_type=='folder':
        try:
            file=Folder.objects.get(id=file_id,is_deleted=True)
        except Folder.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
        #先判断父文件夹
        #父文件夹为空或者父文件夹存在的时候，都需要判断 自己是否有副本
        if file.parent_folder is None or file.parent_folder.is_deleted==False :
            try:
                copy=Copy.objects.get(original=file)
                revised=copy.revised
                folder_list=Folder.objects.filter(parent_folder=revised)
                folder_list.update(parent_folder=file)
                document_list=Document.objects.filter(folder=revised)
                document_list.update(folder=file)
                prototype_list=Prototype.objects.filter(folder=revised)
                prototype_list.update(folder=file)
            except Copy.DoesNotExist:
                pass
            file.is_deleted=False
            file.save()
        else:#if file.parent_folder.is_deleted==True:
            parent_folder=file.parent_folder
            try:
                copy = Copy.objects.get(original=parent_folder)
            except Copy.DoesNotExist:
                folder = Folder.objects.create(name=parent_folder.name, project=parent_folder.project)
                copy = Copy.objects.create(original=parent_folder, revised=folder)
            file.parent_folder = copy.revised
            file.is_deleted = False
            file.save()
    elif file_type=='document':
        try:
            file=Document.objects.get(id=file_id,is_deleted=True)
        except Folder.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文档不存在"})
        #判断父文件夹 存在：
        if file.folder.is_deleted==False:
            file.is_deleted = False
            file.save()
        else:
            parent_folder = file.folder
            try:
                copy=Copy.objects.get(original=parent_folder)
            except Copy.DoesNotExist:
                folder = Folder.objects.create(name=parent_folder.name, project=parent_folder.project)
                copy = Copy.objects.create(original=parent_folder, revised=folder)
            file.parent_folder = copy.revised
    else:
        try:
            file=Prototype.objects.get(id=file_id,is_deleted=True)
        except Prototype.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "原型设计不存在"})
        # 判断父文件夹 存在：
        if file.folder.is_deleted == False:
            file.is_deleted = False
            file.save()
        else:
            parent_folder = file.folder
            try:
                copy = Copy.objects.get(original=parent_folder)
            except Copy.DoesNotExist:
                folder = Folder.objects.create(name=parent_folder.name, project=parent_folder.project)
                copy = Copy.objects.create(original=parent_folder, revised=folder)
            file.parent_folder = copy.revised
    return JsonResponse({'errno': 0, 'msg': "项目恢复成功"})

def rename_folder(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    folder_id=request.POST.get('folder_id')
    name=request.POST.get('name')
    try:
        folder=Folder.objects.get(id=folder_id)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
    if folder.parent_folder is None:
        return JsonResponse({'errno': 1, 'msg': "顶级文件夹不可改名"})
    folder.name=name
    folder.save()
    return JsonResponse({'errno': 0, 'msg': "名称修改成功"})