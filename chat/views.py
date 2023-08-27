import datetime

from django.db.models import Max
from django.http import JsonResponse

from chat.models import UserTeamChatStatus, ChatMessage, Notice
from team.models import Team, Member
from user.cos_utils import get_cos_client
from user.models import User
import uuid
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


def save_message(message,team_id,user_id):
    # 假设你有一个名为ChatMessage的模型，用于存储消息
    ChatMessage.objects.create(team_id=team_id, message=message, user_id=user_id)
    max_index_for_user = UserTeamChatStatus.objects.filter(user_id=user_id).aggregate(Max('index'))['index__max'] or 0
    user_team_chat_status = UserTeamChatStatus.objects.get(user_id=user_id, team_id=team_id)
    user_team_chat_status.index = max_index_for_user + 1
    user_team_chat_status.save()


def upload_image(request, team_id, user_id):
    avatar = request.FILES.get('avatar')
    if not avatar:
        print("no avatar")
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_string = f"team_id: {team_id}, user_id: {user_id}, time: {current_time}"
    print(formatted_string)
    avatar_url, content = upload_cover_method(avatar,formatted_string,'chat_avatar')
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{team_id}",
        {
            'type': 'new_file_uploaded',
            'file_url': avatar_url,
            'file_type': 'image',
        }
    )
    save_message(avatar_url,team_id,user_id)

    return JsonResponse({'errno': 0, 'msg': '上传成功', 'url': avatar_url})




def initial_chat(request,user_id):
    Team_ids= Member.objects.filter(user_id= user_id).values('team_id')
    rooms=[]
    print(Team_ids)
    for team_dict in Team_ids:
        team_id = team_dict['team_id']
        members = Member.objects.filter(team_id=team_id)
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
            })
        try:
            user_team_chat_status = UserTeamChatStatus.objects.get(user_id=user_id, team_id=team_id)
            unread_count = user_team_chat_status.unread_count
            index=user_team_chat_status.index
        except UserTeamChatStatus.DoesNotExist:
            unread_count = 0
            index=1000000

        room_data={
            'roomId':str(team_id),
            'roomName':Team.objects.get(id=team_id).name,
            'unreadCount':unread_count,
            'avatar':Team.objects.get(id=team_id).cover_url,
            'index':index,
            'lastMessage':lastMessage,
            'users':users,
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
    response_submit = client.get_object_sensitive_content_recognition(
        Bucket=bucket_name,
        BizType='aa3bbd2417d7fa61b38470534735ff20',
        Key=cover_key,
    )
    return cover_url, None


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

