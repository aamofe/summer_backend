import datetime
import json

from django.db.models import Max
from django.http import JsonResponse

from chat.models import UserTeamChatStatus, ChatMessage, Notice
from chat.models import Group, ChatMember
from user.cos_utils import get_cos_client
from user.models import User
import uuid
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync





def save_message(message,team_id,user_id):
    # 假设你有一个名为ChatMessage的模型，用于存储消息
    ChatMessage.objects.create(team_id=team_id, message=message, user_id=user_id)



def upload_file(request, team_id, user_id):
    avatar = request.FILES.get('avatar')
    if not avatar:
        print("no avatar")
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_string = f"team_id: {team_id}, user_id: {user_id}, time: {current_time}"
    print(formatted_string)
    avatar_url, contenttype = upload_cover_method(avatar,formatted_string,'chat_avatar')
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{team_id}",
        {
            'type': 'new_file_uploaded',
            'file_url': avatar_url,
            'file_type': contenttype,
        }
    )
    return JsonResponse({'errno': 0, 'msg': '上传成功', 'url': avatar_url})




def initial_chat(request,user_id):
    Team_ids= ChatMember.objects.filter(user_id= user_id).values('team_id')
    rooms=[]
    print(Team_ids)
    for team_dict in Team_ids:
        team_id = team_dict['team_id']
        members = ChatMember.objects.filter(team_id=team_id)
        last_message = ChatMessage.objects.filter(team_id=team_id).order_by('-timestamp').first()
        if not last_message:
            lastMessage = {
                'content': '',
                'username': '',
                'timestamp': '',
            }

        elif last_message.message == '':
            lastMessage = {
                'content': '新文件请查看',
                'username': User.objects.get(id=last_message.user_id).username,
                'timestamp': last_message.timestamp.strftime('%Y/%m/%d/%H:%M'),
            }
        else:
            lastMessage={
                'content':last_message.message,
                'username':User.objects.get(id=last_message.user_id).username,
                'timestamp':last_message.timestamp.strftime('%Y/%m/%d/%H:%M'),
            }
        users = []
        for member in members:
            users.append({
                '_id':str(member.user_id),
                'username':User.objects.get(id=member.user_id).username,
                'avatar':User.objects.get(id=member.user_id).avatar_url,
                'role':member.role,
            })
        try:
            user_team_chat_status = UserTeamChatStatus.objects.get(user_id=user_id, team_id=team_id)
            unread_count = user_team_chat_status.unread_count
            index=user_team_chat_status.index
        except UserTeamChatStatus.DoesNotExist:
            UserTeamChatStatus.objects.create(user_id=user_id, team_id=team_id, unread_count=0, index=0)


        room_data={
            'roomId':str(team_id),
            'roomName':Group.objects.get(id=team_id).name,
            'unreadCount':unread_count,
            'avatar':Group.objects.get(id=team_id).cover_url,
            'index':index,
            'lastMessage':lastMessage,
            'users':users,
            'type':Group.objects.get(id=team_id).type,
        }
        rooms.append(room_data)
    return JsonResponse({'rooms':rooms})



def upload_cover_method(cover_file, cover_id, url):
    client, bucket_name, bucket_region = get_cos_client()
    if cover_id == '' or cover_id == 0:
        cover_id = str(uuid.uuid4())
    file_name = cover_file.name
    file_extension = file_name.split('.')[-1]  # 获取文件后缀
    if file_extension == 'jpg':
        ContentType = "image/jpg"
    elif file_extension == 'jpeg':
        ContentType = "image/jpeg"
    elif file_extension == 'png':
        ContentType = "image/png"
    elif file_extension == 'pdf':
        ContentType = "application/pdf"
    elif file_extension == 'md':
        ContentType = "text/markdown"
    elif file_extension == 'mp3':
        ContentType = "audio/mp3"
    elif file_extension == 'mp4':
        ContentType = "video/mp4"
    else:return -2
    cover_key = f"{url}/{cover_id}.{file_extension}"
    response_cover = client.put_object(
        Bucket=bucket_name,
        Body=cover_file,
        Key=cover_key,
        StorageClass='STANDARD',
        ContentType=ContentType
    )
    if 'url' in response_cover:
        cover_url = response_cover['url']
    else:
        cover_url = f'https://{bucket_name}.cos.{bucket_region}.myqcloud.com/{cover_key}'
    return cover_url, ContentType


def get_user_messages(request, user_id):
    if request.method == "GET":
        user = User.objects.get(id=user_id)
        notices = Notice.objects.filter(receiver=user).order_by('-timestamp')
        data = [{"id": notice.id, "type": notice.notice_type, "url": notice.url, "is_read": notice.is_read} for notice in notices]
        return JsonResponse(data, safe=False)
    return JsonResponse({"error": "Method not allowed"}, status=405)

def get_unread_messages(request, user_id):
    if request.method == "GET":
        user = User.objects.get(id=user_id)
        unread_notices = Notice.objects.filter(receiver=user, is_read=False).order_by('-timestamp')
        data = [{"id": notice.id, "type": notice.notice_type, "url": notice.url} for notice in unread_notices]
        return JsonResponse(data, safe=False)
    return JsonResponse({"error": "Method not allowed"}, status=405)

def make_notice_read(request, notice_id):
    if request.method == "POST":
        notice = Notice.objects.get(id=notice_id)
        if not notice.is_read:
            notice.is_read = True
            notice.save()
        return JsonResponse({"message": "All messages marked as read"})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def make_notice_unread(request, notice_id):
    if request.method == "POST":
        notice = Notice.objects.get(id=notice_id)
        if notice.is_read:
            notice.is_read = False
            notice.save()
        return JsonResponse({"message": "All messages marked as unread"})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def mark_all_as_read(request, user_id):
    if request.method == "PUT":
        user = User.objects.get(id=user_id)
        Notice.objects.filter(receiver=user, is_read=False).update(is_read=True)
        return JsonResponse({"message": "All messages marked as read"})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def delete_notice(request, notice_id):
    if request.method == "DELETE":
        Notice.objects.get(id=notice_id).delete()
        return JsonResponse({"message": "Notice deleted successfully"})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def delete_all_read(request, user_id):
    if request.method == "DELETE":
        user = User.objects.get(id=user_id)
        Notice.objects.filter(receiver=user, is_read=True).delete()
        return JsonResponse({"message": "All read messages deleted"})
    return JsonResponse({"error": "Method not allowed"}, status=405)

def get_group_id(request,team_id):
    group_id=Group.objects.get(actual_team=team_id).id
    return JsonResponse({'group_id':group_id})

def get_group_members(request,group_id):
    members=ChatMember.objects.filter(team_id=group_id)
    data=[]
    for member in members:
        data.append({
            'id':member.user_id,
            'username':User.objects.get(id=member.user_id).username,
            'nickname':User.objects.get(id=member.user_id).nickname,
            'avatar_url':User.objects.get(id=member.user_id).avatar_url,
            'role':member.role,
        })
    return JsonResponse({'members':data})


def get_all_groups_members(request, user_id):
    # 获取该用户所在的所有小组
    groups = ChatMember.objects.filter(user_id=user_id)

    # 使用集合存储已添加的用户ID
    added_users = set()
    data = []

    for group in groups:
        # 使用distinct()去重
        members = ChatMember.objects.filter(team_id=group.team_id).distinct()

        for member in members:
            # 如果该用户ID已在集合中，跳过
            if member.user_id in added_users or member.user_id == user_id:
                continue

            user_info = User.objects.get(id=member.user_id)
            data.append({
                'id': member.user_id,
                'username': user_info.username,
                'nickname': user_info.nickname,
                'avatar_url': user_info.avatar_url,
                'role': member.role,
            })

            # 添加用户ID到集合中
            added_users.add(member.user_id)

    return JsonResponse({'members': data})



def get_group(request, user_id):
    groups = ChatMember.objects.filter(user_id=user_id)
    data = []
    for group in groups:
        data.append(group.team_id)
    return JsonResponse({'groups': data})

def make_group(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        creator_id = data.get('creator_id')
        invitees = data.get('invitees', [])
        description = data.get('description', '')
        cover_url = data.get('url')

        user_ids = invitees + [creator_id]
        # 查询对应的用户对象，根据invitees中的用户ID
        user_objects = User.objects.filter(id__in=user_ids)

        # 提取每个用户对象的用户名字
        user_names_list = [user.username for user in user_objects]

        # 将用户名列表用逗号和空格连接成字符串
        name= "、".join(user_names_list)

        try:
            creator = User.objects.get(pk=creator_id)
        except User.DoesNotExist:
            return JsonResponse({"error": "Creator not found"}, status=400)

        group = Group(
            name=name,
            user=creator,
            description=description,
            cover_url=cover_url,
            type='group'
        )
        group.save()

        ChatMember(user=creator, team=group, role='CR').save()
        UserTeamChatStatus(user=creator, team=group, unread_count=0, index=0).save()
        channel_layer=get_channel_layer()


        for invitee_id in invitees:
            try:
                invitee = User.objects.get(pk=invitee_id)
                ChatMember(user=invitee, team=group,role='MB').save()
                UserTeamChatStatus(user=invitee, team=group, unread_count=0, index=0).save()

            except User.DoesNotExist:
                # Handle or log error if the invitee doesn't exist.
                # For this example, I'll just continue to the next invitee.
                continue
        users = []
        members = ChatMember.objects.filter(team_id=group.id)
        for member in members:
            users.append({
                '_id': str(member.user_id),
                'username': User.objects.get(id=member.user_id).username,
                'avatar': User.objects.get(id=member.user_id).avatar_url,
            })
        data = {

            'roomId': str(group.id),
            'roomName': group.name,
            'unreadCount': 0,
            'avatar': group.cover_url,
            'index': 0,
            'lastMessage': '',
            'users': users,
        }

        room = [data]
        async_to_sync(channel_layer.group_send)(
            "notification_group",
            {
                'type': 'new_group_chat',
                'room': room,
            }
        )
        return JsonResponse({'group_id': group.id})

    else:
        return JsonResponse({"error": "Invalid request method"}, status=400)

