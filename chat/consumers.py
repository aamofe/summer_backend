import json
import re

from django.db.models import F, Max
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from chat.models import ChatMessage, Notice, UserTeamChatStatus, UserChatChannel, UserNoticeChannel
from user.models import User
from .models import ChatMember, Group


class TeamChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = None

    async def connect(self):
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f"chat_{self.team_id}"
        await self.save_user_chat_channel()

        # 将用户加入到团队群聊
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        # 将用户和团队信息存储到信息状态表中
        ''''
        latest_message = await self.get_latest_message()
        unread_count = await self.get_unread_count()

        await self.send(text_data=json.dumps({
            'message': latest_message.message if latest_message else None,
            'username': await self.get_username(latest_message.user_id) if latest_message else None,
            'avatar_url': await self.get_avatar_url(latest_message.user_id) if latest_message else None,
            'time': latest_message.timestamp.strftime('%Y-%m-%d %H:%M:%S') if latest_message else None,
            'unread_count': unread_count
        }))
        '''''
    async def disconnect(self, close_code):
        # 将用户从团队群聊中移除
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        if 'all' in text_data_json:
            recent_messages = await self.get_recent_messages()
            user_id = text_data_json['user_id']
            # 创建一个空数组来存放所有消息
            messages_array = []

            # 遍历每条消息并将其添加到消息数组中
            for msg in recent_messages:
                message_data = {
                    'message': msg.message,
                    'user_id': str(msg.user_id),
                    'username': await self.get_username(msg.user_id),
                    'files': msg.files,
                    'replyMessage': msg.reply_message,
                    'avatar_url': await self.get_avatar_url(msg.user_id),
                    'time': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                messages_array.append(message_data)

            # 一次性发送整个消息数组
            await self.send(text_data=json.dumps({
                'messages': messages_array
            }))
            await self.mark_messages_as_read(user_id)

        elif 'clean' in text_data_json:
            await self.mark_messages_as_read(self.user_id)
        else:
            # 检查是否是搜索请求
            if 'status' in text_data_json:
                user_id = text_data_json['user_id']
                await self.send_chat_status(user_id)
                return
            if 'search' in text_data_json:####################################################还需要改动（增加）
                keyword = text_data_json['search']
                search_results = await self.search_messages(keyword)
                await self.send(text_data=json.dumps({
                    'search_results': search_results
                }))
                return
            user_id = text_data_json['user_id']
            message = text_data_json.get('message', '')  # 如果'message'不存在，返回空字符串
            files = text_data_json.get('files', [])  # 如果'files'不存在，返回空列表
            replyMessage = text_data_json.get('replyMessage', {})  # 如果'reply_message'不存在，返回空字典
            await self.save_message(message,user_id,files,replyMessage)
            await self.index_up(user_id,self.team_id)
            # 将消息发送给团队群聊的所有成员
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'files': files,
                    'user_id': user_id,
                    'replyMessage': replyMessage,
                    'username': await self.get_username(user_id),
                    'avatar_url': await self.get_avatar_url(user_id),
                    'time': await self.get_time(),
                }
            )
            await self.increment_and_notify(user_id)
            await self.mark_messages_as_read(user_id)

            '''''''''
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_status',
                    'unread_count': await self.get_unread_count(self.user_id),
                    'latest_message': message,
                    'team_name': await self.get_team_name(self.team_id),
                    'cover_url': await self.get_cover_url(self.team_id),
                }
            )
            '''''''''
            if '@所有人' in message:
                await self.handle_mention_all(message)
            else:
                mentioned_users = set(re.findall(r'@(\w+)', message))
                for user in mentioned_users:
                    await self.handle_mention(user, message)

    async def chat_message(self, event):
        user_id = event['user_id']
        message = event['message']
        username = event.get('username', '')
        avatar_url = event.get('avatar_url', '')
        time = event.get('time', '')
        files = event.get('files', [])  # 获取files字段，如果没有则默认为空列表
        replyMessage = event.get('replyMessage', None)  #
        print(replyMessage)
        # 发送消息给 WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'team_id': self.team_id,
            'user_id': user_id,
            'message': message,
            'files': files,
            'replyMessage': replyMessage,
            'username': username,
            'avatar_url': avatar_url,
            'time': time
        }))

    async def new_file_uploaded(self, event):
        # Handle the logic for the new_file_uploaded event
        await self.send(text_data=json.dumps({
            'file_url': event['file_url'],
            'file_type': event['file_type'],
        }))

    async def chat_status(self, event):
        unread_count = event['unread_count']
        latest_message = event['latest_message']
        username = event.get('username', '')
        time = event.get('time', '')
        index = event.get('index', '')
        await self.send(text_data=json.dumps({
            'type': 'chat_status',
            'team_id': self.team_id,
            'username': username,
            'index': index,
            'time': time,
            'unread_count': unread_count,
            'latest_message': latest_message,
        }))
    @database_sync_to_async
    def save_message(self, message,user_id,files,reply_message):
        # 假设你有一个名为ChatMessage的模型，用于存储消息
        ChatMessage.objects.create(team_id=self.team_id, message=message,user_id=user_id,files=files,reply_message=reply_message)


    @database_sync_to_async
    def search_messages(self, keyword):
        # 搜索包含关键字的消息
        messages = ChatMessage.objects.filter(team_id=self.team_id, message__icontains=keyword)
        return [msg.message for msg in messages]
    @database_sync_to_async
    def create_notice(self, user_id, message):
        Notice.objects.create(user_id=user_id, message=message)
    async def handle_mention(self, username, original_message):
        user = await self.get_user(username)
        if user:
            notice_message = f"You were mentioned in a message: '{original_message}'"
            await self.create_notice(user.id, notice_message)
    async def handle_mention_all(self, original_message):
        users = await self.get_users()
        for user in users:
            notice_message = f"You were mentioned in a message: '{original_message}'"
            await self.create_notice(user.id, notice_message)
    @database_sync_to_async
    def get_user(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None
    @database_sync_to_async
    def get_users(self):
        try:
            user_ids = ChatMember.objects.filter(team_id=self.team_id).values_list('user_id', flat=True)
            users = User.objects.filter(id__in=user_ids)
            return list(users)
        except User.DoesNotExist:
            return None
    @database_sync_to_async
    def get_username(self, user_id):
        try:
            return User.objects.get(id=user_id).username
        except User.DoesNotExist:
            return None
    @database_sync_to_async
    def get_avatar_url(self, user_id):
        try:
            return User.objects.get(id=user_id).avatar_url
        except User.DoesNotExist:
            return None
    @sync_to_async
    def get_time(self):
        return timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    @database_sync_to_async
    def index_up(self, user_id, team_id):
        from django.db.models import Max
        # 获取最大index值
        max_index = UserTeamChatStatus.objects.filter(user_id=user_id).aggregate(Max('index'))['index__max'] or 0

        # 使用get_or_create获取或创建对象
        user_team_chat_status, created = UserTeamChatStatus.objects.get_or_create(user_id=user_id, team_id=team_id)

        # 设置index为最大值加1
        user_team_chat_status.index = max_index + 1
        user_team_chat_status.save()

    @database_sync_to_async
    def increment_unread_count_and_index_in_db(self, user_id):
        user_ids = ChatMember.objects.filter(team_id=self.team_id).values_list('user_id', flat=True)
        new_user_ids = user_ids.exclude(user_id=user_id)

        for uid in new_user_ids:
            status, created = UserTeamChatStatus.objects.get_or_create(user_id=uid, team_id=self.team_id,
                                                                       defaults={'unread_count': 0})
            if created:
                # 如果创建了新的记录, 设置unread_count为1
                status.unread_count = 1
                status.index = 1
            else:
                # 否则增加unread_count
                status.unread_count += 1
                self.index_up(uid, self.team_id)
            status.save()
        return user_ids

    @database_sync_to_async
    def get_user_ids(self, user_ids_query):
        return list(user_ids_query)
    # This method can be used to send messages using channel_layer
    def return_message(self, message):
        result= message.message if message.message else "新文件请查看"
        print(result)
        return result
    @database_sync_to_async
    def return_username(self, message):
        return User.objects.get(id = message.user_id).username if message else None
    @database_sync_to_async
    def return_time(self, message):
        return message.timestamp.strftime('%Y-%m-%d %H:%M:%S') if message else None
    @database_sync_to_async
    def get_index(self, user_id):
        return UserTeamChatStatus.objects.get(user_id=user_id, team_id=self.team_id).index
    async def notify_users_of_unread_count(self, user_ids):
        user_ids_list = await self.get_user_ids(user_ids)
        for uid in user_ids_list:
            channel_name = await self.get_channel_name_for_user(uid, self.team_id)
            if not channel_name:
                print(f'No channel name for user {uid}')
                continue
            await self.channel_layer.send(channel_name, {
                'type': 'chat_status',
                'unread_count': await self.get_unread_count(uid),
                'index': await self.get_index(uid),
                'username': await self.return_username(await self.get_latest_message()),
                'time': await self.return_time(await self.get_latest_message()),
                'latest_message': self.return_message(await self.get_latest_message()),
                'team_name': await self.get_team_name(self.team_id),
                'cover_url': await self.get_cover_url(self.team_id),
            })


    @database_sync_to_async
    def create_status(self, user_id, team_id):
        if UserTeamChatStatus.objects.filter(user_id=user_id, team_id=team_id).exists():
            return UserTeamChatStatus.objects.get(user_id=user_id, team_id=team_id)
        else:
            status = UserTeamChatStatus.objects.create(user_id=user_id, team_id=team_id, unread_count=0, index=0)
            return status




    # Now, when you want to increment and notify
    async def increment_and_notify(self, user_id):

        user_ids = await self.increment_unread_count_and_index_in_db(user_id)
        await self.notify_users_of_unread_count(user_ids)

    @database_sync_to_async
    def get_channel_name_for_user(self, user_id, team_id):
        print(user_id, self.team_id)
        if UserChatChannel.objects.filter(user_id=user_id,team_id=team_id).exists():
            channel = UserChatChannel.objects.get(user_id=user_id,team_id=team_id)
            return channel.channel_name
        else:
            return None

    async def send_chat_status(self, user_id):
        unread_count = await self.get_unread_count(user_id)
        latest_message = await self.get_latest_message()
        await self.send(text_data=json.dumps({
            'type': 'chat_status',
            'unread_count': unread_count,
            'latest_message': latest_message.message if latest_message else None,

        }))


    @database_sync_to_async
    def get_recent_messages(self):
        return list(ChatMessage.objects.filter(team_id=self.team_id).order_by('timestamp'))

    @database_sync_to_async
    def get_latest_message(self):
        message = ChatMessage.objects.filter(team_id=self.team_id).order_by('-timestamp').first()
        if message:
            return message
        else:
            return None

    @database_sync_to_async
    def get_unread_count(self, user_id):
        status = UserTeamChatStatus.objects.filter(user_id=user_id, team_id=self.team_id).first()
        return status.unread_count if status else 0

    @database_sync_to_async
    def mark_messages_as_read(self, user_id):
        status = UserTeamChatStatus.objects.get(user_id=user_id, team_id=self.team_id)
        status.unread_count = 0
        status.save()


    @database_sync_to_async
    def get_team_name(self, team_id):
        try:
            return Group.objects.get(id=team_id).name
        except Group.DoesNotExist:
            return None

    @database_sync_to_async
    def get_cover_url(self, team_id):
        try:
            return Group.objects.get(id=team_id).cover_url
        except Group.DoesNotExist:
            return None

    @database_sync_to_async
    def save_user_chat_channel(self):
        UserChatChannel.objects.update_or_create(user_id=self.user_id,team_id=self.team_id ,defaults={'channel_name': self.channel_name})

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        # 你可以在这里加入某个group，例如基于聊天室的名字
        await self.channel_layer.group_add("notification_group", self.channel_name)
        await self.save_user_notice_channel()
        await self.accept()

    async def disconnect(self, close_code):
        # 退出group
        await self.channel_layer.group_discard("notification_group", self.channel_name)


    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        if data['type'] == 'chat':
            if data['range'] == 'all':
                # 广播消息给所有人
                await self.channel_layer.group_send("notification_group", {
                    "type": "chat_notice",
                    "url": data['url'],
                    "roomID": data['roomID']
                })
                await self.upload_chat_notice(data['url'], data['roomID'])
            elif data['range'] == 'individual':
                # 发送消息给指定用户
                user_id = data['user_id']  # 假设传来的数据里有目标用户的ID
                channel_name = await self.get_channel_name_for_user(user_id)
                if channel_name:
                # 用channel_name发送消息给指定用户
                    await self.channel_layer.send(channel_name, {
                        "type": "chat_notice",
                        "url": data['url'],
                        "roomID": data['roomID']
                    })
                await self.upload_chat_notice(data['url'], data['roomID'])
        elif data['type'] == 'file':
            user_id = data['user_id']  # 假设传来的数据里有目标用户的ID
            file_id = data['file_id']
            channel_name = await self.get_channel_name_for_user(user_id)
            if channel_name:
                # 用channel_name发送消息给指定用户
                await self.channel_layer.send(channel_name, {
                    "type": "file_notice",
                    "url": data['url'],
                })
            await self.upload_file_notice(data['url'], file_id)




    @database_sync_to_async
    def get_channel_name_for_user(self, user_id):
        if UserNoticeChannel.objects.filter(user_id=user_id).exists():
            channel = UserNoticeChannel.objects.get(user_id=user_id)
            return channel.channel_name
        else:
            return None
    async def chat_notice(self, event):
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'type': 'chat_notice',
            'url': '/chat',
            'roomID': event["roomID"]
        }))
    async def file_notice(self, event):
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'type': 'file_notice',
            'url': event["url"],
        }))
    async def send_notification(self, event):
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'message': event["message"]
        }))
    @database_sync_to_async
    def save_user_notice_channel(self):
        UserNoticeChannel.objects.update_or_create(user_id=self.user_id, defaults={'channel_name': self.channel_name})
    @database_sync_to_async
    def upload_chat_notice(self, url, roomID):
        Notice.objects.create(receiver_id=self.user_id, notice_type='chat_mention', url=url,
                              associated_resource_id=roomID)
    @database_sync_to_async
    def upload_file_notice(self, url, file_id):
        Notice.objects.create(receiver_id=self.user_id, notice_type='document_mention', url=url,
                              associated_resource_id=file_id)
'''''
class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 获取发送者和接收者的用户ID
        self.sender_user_id = self.scope['url_route']['kwargs']['sender_user_id']
        self.receiver_user_id = self.scope['url_route']['kwargs']['receiver_user_id']
        
        # 创建私聊的房间名称
        self.room_name = f"private_chat_{self.sender_user_id}_{self.receiver_user_id}"
        
        unread_count = await self.get_unread_count(self.sender_user_id, self.receiver_user_id)
        latest_message = await self.get_latest_message(self.sender_user_id, self.receiver_user_id)

        # 发送当前未读消息数量和最新消息到 WebSocket 连接
        await self.send(text_data=json.dumps({
            'type': 'chat_status',
            'username': await self.get_username(latest_message.user_id) if latest_message else None,
            'sender_avatar_url': await self.get_avatar_url(latest_message.user_id) if latest_message else None,
            'sender_avatar_url': await self.get_avatar_url(latest_message.user_id) if latest_message else None,
            'time': latest_message.timestamp.strftime('%Y-%m-%d %H:%M:%S') if latest_message else None,
            'unread_count': unread_count,
            'latest_message': latest_message.message if latest_message else None,
        }))
        # 将连接加入到房间
        await self.channel_layer.group_add(
            self.room_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # 将连接从房间移除
        await self.channel_layer.group_discard(
            self.room_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        
        # 将消息发送到房间
        await self.channel_layer.group_send(
            self.room_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_user_id': self.sender_user_id,
                'receiver_user_id': self.receiver_user_id
            }
        )
    
    async def chat_message(self, event):
        message = event['message']
        sender_user_id = event['sender_user_id']
        receiver_user_id = event['receiver_user_id']
        
        # 发送消息到 WebSocket 连接
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message,
            'sender_user_id': sender_user_id,
            'receiver_user_id': receiver_user_id
        }))

    @database_sync_to_async
    def get_unread_count(self, sender_user_id, receiver_user_id):
        # 在此处查询未读消息数量
        # 返回未读消息数量
        pass
    
    @database_sync_to_async
    def get_latest_message(self, sender_user_id, receiver_user_id):
        # 在此处查询最新消息
        # 返回最新消息对象
        pass

'''''
