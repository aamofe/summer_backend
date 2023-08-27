import json
import re

from django.db.models import F, Max
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from chat.models import ChatMessage, Notice, UserTeamChatStatus, UserChatChannel
from user.models import User
from team.models import Member, Team


class TeamChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = None

    async def connect(self):
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f"chat_{self.team_id}"
        await self.save_user_channel()
        # 将用户加入到团队群聊
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        # 将用户和团队信息存储到信息状态表中
        await self.create_user_team_chat_status()
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
            for msg in recent_messages:
                await self.send(text_data=json.dumps({
                    'message': msg.message,
                    'user_id': str(msg.user_id),
                    'username': await self.get_username(msg.user_id),
                    'avatar_url': await self.get_avatar_url(msg.user_id),
                    'time': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }))
            await self.mark_messages_as_read(user_id)
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
            message = text_data_json['message']
            user_id = text_data_json['user_id']
            await self.save_message(message,user_id)

            # 将消息发送给团队群聊的所有成员
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'username': await self.get_username(user_id),
                    'avatar_url': await self.get_avatar_url(user_id),
                    'time': await self.get_time(),
                }
            )
            await self.increment_and_notify(user_id)


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
        message = event['message']
        username = event.get('username', '')
        avatar_url = event.get('avatar_url', '')
        time = event.get('time', '')
        # 发送消息给 WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message,
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
        team_name = event['team_name']
        cover_url = event['cover_url']
        await self.send(text_data=json.dumps({
            'type': 'chat_status',
            'unread_count': unread_count,
            'latest_message': latest_message,
            'team_name': team_name,
            'cover_url': cover_url,
        }))
    @database_sync_to_async
    def save_message(self, message,user_id):
        # 假设你有一个名为ChatMessage的模型，用于存储消息
        ChatMessage.objects.create(team_id=self.team_id, message=message,user_id=user_id)

        max_index_for_user = UserTeamChatStatus.objects.filter(user_id=user_id).aggregate(Max('index'))['index__max'] or 0
        user_team_chat_status = UserTeamChatStatus.objects.get(user_id=user_id, team_id=self.team_id)
        user_team_chat_status.index = max_index_for_user + 1
        user_team_chat_status.save()
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
            user_ids = Member.objects.filter(team_id=self.team_id).values_list('user_id', flat=True)
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
    def increment_unread_count_in_db(self, user_id):
        user_ids = Member.objects.filter(team_id=self.team_id).exclude(user_id=user_id).values_list('user_id',
                                                                                                    flat=True)
        UserTeamChatStatus.objects.filter(user_id__in=user_ids, team_id=self.team_id).update(
            unread_count=F('unread_count') + 1)
        return user_ids

    @database_sync_to_async
    def get_user_ids(self, user_ids_query):
        return list(user_ids_query)
    # This method can be used to send messages using channel_layer
    def return_message(self, message):
        return message.message if message else None

    async def notify_users_of_unread_count(self, user_ids):
        user_ids_list = await self.get_user_ids(user_ids)
        for uid in user_ids_list:
            channel_name = await self.get_channel_name_for_user(uid)
            unread_count = await self.get_unread_count(uid)
            await self.channel_layer.send(channel_name, {
                'type': 'chat_status',
                'unread_count': unread_count,
                'latest_message': self.return_message(await self.get_latest_message()),
                'team_name': await self.get_team_name(self.team_id),
                'cover_url': await self.get_cover_url(self.team_id),
            })

    # Now, when you want to increment and notify
    async def increment_and_notify(self, user_id):
        user_ids = await self.increment_unread_count_in_db(user_id)
        await self.notify_users_of_unread_count(user_ids)


    async def send_chat_status(self, user_id):
        unread_count = await self.get_unread_count(user_id)
        latest_message = await self.get_latest_message()
        await self.send(text_data=json.dumps({
            'type': 'chat_status',
            'unread_count': unread_count,
            'latest_message': latest_message.message if latest_message else None,

        }))

    @database_sync_to_async
    def get_channel_name_for_user(self, user_id):
        print(user_id, self.team_id)
        return UserChatChannel.objects.get(user_id=user_id).channel_name

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
        status, created = UserTeamChatStatus.objects.get_or_create(user_id=user_id, team_id=self.team_id)
        status.unread_count = 0
        status.save()

    @database_sync_to_async
    def create_user_team_chat_status(self):
        if not UserTeamChatStatus.objects.filter(user_id=self.user_id, team_id=self.team_id).exists():
            from django.db.models import Max
            max_index = UserTeamChatStatus.objects.aggregate(Max('index'))['index__max'] or 0
            UserTeamChatStatus.objects.get_or_create(user_id=self.user_id, team_id=self.team_id,index=max_index+1)


    @database_sync_to_async
    def get_team_name(self, team_id):
        try:
            return Team.objects.get(id=team_id).name
        except Team.DoesNotExist:
            return None

    @database_sync_to_async
    def get_cover_url(self, team_id):
        try:
            return Team.objects.get(id=team_id).cover_url
        except Team.DoesNotExist:
            return None

    @database_sync_to_async
    def save_user_channel(self):
        UserChatChannel.objects.update_or_create(user_id=self.user_id, defaults={'channel_name': self.channel_name})

#class NoticeConsumer:
