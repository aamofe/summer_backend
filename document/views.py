import json
import pprint
import uuid

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from jose import ExpiredSignatureError, JWTError
import jwt
from django.contrib.auth.models import AnonymousUser
from document.models import Document, Prototype, History, Folder 
from summer_backend import settings
from summer_backend.settings import SECRET_KEY
from team.models import Team, Member, Project
from user.authentication import validate_login, validate_all
from user.cos_utils import get_cos_client
from user.models import User
from user.views import upload_cover_method
@validate_login
def share_document(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    document_id=request.POST.get('document_id')
    try :
        document=Document.objects.get(id=document_id,parent_folder__is_deleted=False)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    payload = {"document_id":document_id}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    url="http://www.aamoef.top/tiptap/"+token+'/'
    return JsonResponse({'errno':0,'data':{'url':url}})

@validate_login
def update_document_permisson(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    document_id=request.POST.get('document_id')
    editable=request.POST.get('editable')
    user=request.user
    try :
        document=Document.objects.get(id=document_id,parent_folder__is_deleted=False)
    except Document.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    try:
        editable = int(editable)  # 将字符串转换为整数
    except (ValueError, TypeError):
        return JsonResponse({'errno': 1, 'msg': "编辑权限错误"})
    if editable != 1 and editable != 0:
        return JsonResponse({'errno': 1, 'msg': "编辑权限错误"})
    try:
        member=Member.objects.get(team=document.parent_folder.project.team,user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if member.role=='MB':
        return JsonResponse({'errno': 1, 'msg': "用户权限不足"})
    document.editable=True if editable==1 else False
    document.save()
    print(document.editable)
    return JsonResponse({'errno': 0, 'msg': "修改权限成功"})
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
        editable=document.editable
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
@validate_login
def create(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    file_type = request.POST.get('file_type')  # 原型 文档
    parent_folder_id=request.POST.get('parent_folder_id')
    title = request.POST.get("title")
    content = request.POST.get("content")
    if not title or not file_type or not title or not parent_folder_id :
        return JsonResponse({'errno': 1, 'msg': "参数不全"})
    if not(file_type=='document' or file_type=='prototype'):
        return JsonResponse({'errno': 1, 'msg': "创建文件类型错误"})
    try:
        parent_folder = Folder.objects.get(id=parent_folder_id,is_deleted=False)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
    try:
        member = Member.objects.filter(team=parent_folder.project.team, user=user)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    if file_type=='document':
        file = Document.objects.create(title=title,parent_folder=parent_folder, user=user)
    else:
        file = Prototype.objects.create(title=title,parent_folder=parent_folder, user=user)
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
    file_id=request.POST.get('file_id') #删除1个
    # forerver=request.POST.get('forever')#0代表否 1代表是
    if not file_type  or not file_id:
        return JsonResponse({'errno': 1, 'msg': "参数不全"})
    if not(file_type in {'document','prototype','folder'}) or not file_id.isdigit() :
        return JsonResponse({'errno': 1, 'msg': "参数值错误"})
    if file_type=='folder':
        try:
            folder=Folder.objects.get(id=file_id,is_deleted=False)
        except Folder.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
        try:
            member = Member.objects.get(user=user, team=folder.project.team)
        except Member.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
        if folder.is_deleted:
            return JsonResponse({'errno': 1, 'msg': "文件夹已被删除"})
        else:
            folder.is_deleted=True
            folder.deleted_at=timezone.now()
            folder.save()
        return JsonResponse({'errno': 0, 'msg': "文件夹删除成功"})
    #我是文档/原型
    if file_type == 'document':
        try:
            file=Document.objects.get(id=file_id,is_deleted=False,parent_folder__is_deleted=False)
        except Document.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文档不存在"})
    elif file_type=='prototype':
        try:
            file = Prototype.objects.get(id=file_id,is_deleted=False,parent_folder__is_deleted=False)
        except Project.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "原型不存在"})
    parent_folder=file.parent_folder
    try:
        member = Member.objects.get(user=user, team=parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    file.is_deleted=True
    file.deleted_at=timezone.now()
    file.save()
    return JsonResponse({'errno': 0, 'msg': "删除成功"})

@validate_login
def save(request):
    if request.method!='POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    content=request.POST.get('content')
    file_type = request.POST.get('file_type')  # 原型 文档
    file_id = request.POST.get('file_id')  # 保存1个
    # parent_folder_id = request.POST.get('parent_folder_id')
    title=request.POST.get('title')
    user=request.user
    if not file_type or not file_id :
        return JsonResponse({'errno': 1, 'msg': "参数不全"})
    if not(file_type=='document' or file_type=='prototype' or file_type=='folder') or not file_id.isdigit() :
        print('错误 ： ',file_type,file_id)
        return JsonResponse({'errno': 1, 'msg': "参数值错误"})
    if file_type=='folder':
        try:
            folder=Folder.objects.get(id=file_id)
        except Folder.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
        if folder.parent_folder is None:
            return JsonResponse({'errno': 1, 'msg': "顶级文件夹不可改名"})
        if not title:
            return JsonResponse({'errno': 1, 'msg': "请输入文件夹名称"})
        print('tile :',title)
        folder.name=title
        folder.save()
        return JsonResponse({'errno': 0, 'msg': "名称修改成功"})
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
    parent_folder=file.parent_folder
    if parent_folder.is_deleted:
        return JsonResponse({'errno': 1, 'msg': "文件夹已被删除"})
    try:
        member = Member.objects.get(user=user, team=parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    
    if title:
        file.title=title
    if content:
        file.content=content
        if file_type=='document':
            history=History.objects.create(document=file,content=content,user=user)
    file.save()
    return JsonResponse({'errno': 0, 'msg': "内容已保存"})

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
    deleted_documents = Document.objects.filter(Q(parent_folder__project=project, is_deleted=True))
    deleted_prototype = Prototype.objects.filter(Q(parent_folder__project=project, is_deleted=True))
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
    # project_id = request.POST.get('project_id')
    
    parent_folder_id = request.POST.get('parent_folder_id')  # 修改参数名为 parent_folder_id
    if parent_folder_id:
        try:
            parent_folder = Folder.objects.get(id=parent_folder_id,is_deleted=False)
        except Folder.DoesNotExist:
            return JsonResponse({'errno': 1, 'msg': "父文件夹不存在"})
    else:
       return JsonResponse({'errno': 1, 'msg': "请传入父文件夹id"})
    project=parent_folder.project
    if project.is_deleted:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member=Member.objects.get(user=user,team=parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    
    if parent_folder.parent_folder!=None:
        return JsonResponse({'errno': 1, 'msg': "不可创建三级文件夹"})
    folder_name = request.POST.get('folder_name')  # 从请求中获取文件夹名
    if not folder_name:
        return JsonResponse({'errno': 1, 'msg': "文件夹名称不能为空"})
    folder = Folder.objects.create(name=folder_name, project=project, user=user, parent_folder=parent_folder)
    folders={'folder_id':folder.id}
    return JsonResponse({'errno': 0, 'msg': "文件夹创建成功", 'folder':folders})



@validate_login
def view_folder(request):
    if request.method != 'GET':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误！"})
    # project_id = request.GET.get('project_id')
    parent_folder_id = request.GET.get('parent_folder_id')
    sorted_by=request.GET.get('sorted_by','created_at')
    if sorted_by not in{'created_at','-created_at','name','-name'}:
        return JsonResponse({'errno': 1, 'msg': "排序方法错误"})
    try:
        parent_folder = Folder.objects.get(id=parent_folder_id,is_deleted=False)
    except Folder.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "文件夹不存在"})
    user=request.user
    project=parent_folder.project
    pprint.pprint(project.to_dict())
    print(project.is_deleted)
    if project.is_deleted:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    try:
        member=Member.objects.get(user=user,team=parent_folder.project.team)
    except Member.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "用户不属于该团队"})
    
    parent_folder_info = parent_folder.to_dict(sorted_by)
    return JsonResponse({'errno': 0, 'msg': "获取文件夹信息成功", 'parent_folder': parent_folder_info})

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
            file.is_deleted=False
            file.save()
        else:#if file.parent_folder.is_deleted==True:
            parent_folder=file.parent_folder
            return JsonResponse({'errno': 1, 'msg': "父文件夹已被删除"})
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
            return JsonResponse({'errno': 1, 'msg': "父文件夹已被删除"})
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
            return JsonResponse({'errno': 1, 'msg': "父文件夹不存在"})
    return JsonResponse({'errno': 0, 'msg': "文档恢复成功"})

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

@validate_login
def upload(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    file_type=request.POST.get('file_type')
    file=request.FILES.get('file')
    if not file_type in {'document','prototype'}:
        return JsonResponse({'errno': 1, 'msg': "文件类型不合法"})
    if not file:
         return JsonResponse({'errno': 1, 'msg': "请上传文件"})
    res,url=upload_cover_method(file,0,file_type)
    if res == -1:
        return JsonResponse({'errno': 1, 'msg': "图片格式不合法"})
    else:
        return JsonResponse({'errno':0,'url':url,'msg':'上传图片成功'})

@validate_login 
def delete_permanently(request):
    if request.method != 'POST':
        return JsonResponse({'errno': 1, 'msg': "请求方法错误"})
    user = request.user
    project_id = request.GET.get('project_id')
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'errno': 1, 'msg': "项目不存在"})
    deleted_folders = Folder.objects.filter(project=project, is_deleted=True)
    deleted_folders.delete()
    deleted_documents = Document.objects.filter(Q(parent_folder__project=project, is_deleted=True))
    deleted_documents.delete()
    deleted_prototype = Prototype.objects.filter(Q(parent_folder__project=project, is_deleted=True))
    deleted_prototype.delete()
    return JsonResponse({'errno': 0, 'msg': "已彻底删除"})