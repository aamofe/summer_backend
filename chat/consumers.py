import asyncio
from datetime import datetime
import json
import re

from channels.layers import get_channel_layer
from django.db.models import F, Max
from django.utils import timezone
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async, async_to_sync
from chat.models import ChatMessage, Notice, UserTeamChatStatus, UserChatChannel, UserNoticeChannel, File
from team.models import Member
from user.models import User
from . import online_users
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

            messages_array = await self.build_message_array()

            # 一次性发送整个消息数组
            await self.send(text_data=json.dumps({
                'messages': messages_array
            }))
            await self.mark_messages_as_read(user_id)
        elif 'delete_personal' in text_data_json:
            deleter_id=text_data_json['deleter_id']
            await self.delete_user(deleter_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_delete_personal',
                    'roomID':self.team_id,
                    'deleter_id':deleter_id,
                }
            )
            return
        elif 'delete_all' in text_data_json:
            await self.delete_group()
            await self.channel_layer.group_send(
                'notification_group',
                {
                    'type': 'chat_delete_all',
                    'roomID':self.team_id,
                }
            )
        elif 'forward_all'in text_data_json:
            message_ids = text_data_json['message_ids']
            group_id = text_data_json.get('group_id', '')
            group_name = f"chat_{group_id}"
            replyMessage = text_data_json.get('replyMessage', {})  # 如果'reply_message'不存在，返回空字典
            chatMessage=await self.forward_messages_as_combined(message_ids,replyMessage,group_id)
            await self.channel_layer.group_send(
                group_name,
                {
                    'type': 'chat_forward_message',
                    'team_id': group_id,
                    'message': await self.to_dict(chatMessage),
                }
            )
            await self.notify(self.user_id)
        elif 'forward_single' in text_data_json:
            message_ids = text_data_json['message_ids']
            group_id = text_data_json.get('group_id', '')
            group_name = f"chat_{group_id}"
            replyMessage = text_data_json.get('replyMessage', {})
            for message_id in message_ids:
                chatMessage = await self.handle_foward_single(message_id, group_id)
                await self.channel_layer.group_send(
                    group_name,
                    {
                        'type': 'chat_message',
                        'user_id': self.user_id,
                        'team_id': group_id,
                        'message_id': await self.get_latest_message_id(),
                        'message': '群聊的聊天记录',
                        'files': await self.get_files(chatMessage),
                        'date': chatMessage.date,
                        'replyMessage': chatMessage.reply_message,
                        'username': await self.get_username(chatMessage.user_id),
                        'avatar_url': await self.get_avatar_url(chatMessage.user_id),
                        'time': await self.get_time(),
                    }
                )
                print('single before')
                await self.notify(self.user_id)
                print('single after')
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
            date = text_data_json.get('date', '')
            replyMessage = text_data_json.get('replyMessage', {})  # 如果'reply_message'不存在，返回空字典
            file_data = text_data_json.get('files', None)  # 如果'files'不存在，返回空列表
            if file_data is not None and isinstance(file_data, list) and len(file_data) > 0:
                file_data_item = file_data[0]
                await self.handle_files(file_data_item, message, user_id, replyMessage,date)
            else:
                await self.upload_chatmessage(message, user_id, replyMessage,date)
                file_data_item = None


            # 将消息发送给团队群聊的所有成员
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': await self.get_latest_message_id(),
                    'message': message,
                    'files': file_data_item,
                    'date': date,
                    'user_id': user_id,
                    'replyMessage': replyMessage,
                    'username': await self.get_username(user_id),
                    'avatar_url': await self.get_avatar_url(user_id),
                    'time': await self.get_time(),
                }
            )

            await self.notify(user_id)

            print('index up over')
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

    @database_sync_to_async
    def get_recent_messages(self):
        #获取最近10条
        return ChatMessage.objects.filter(team_id=self.team_id).order_by('-timestamp')[:10]

    async def build_message_array(self):
        recent_messages = await self.get_recent_messages()
        messages_array = []

        for msg in recent_messages:
            forwarded_messages = []
            if msg.is_forwarded:
                forwarded_messages.append(await self.to_dict(msg))
            message_data = {
                'message_id': msg.id,
                'message': msg.message,
                'user_id': str(msg.user_id),
                'username': await self.get_username(msg.user_id),
                'files': await self.get_files(msg),
                'date': msg.date,
                'replyMessage': msg.reply_message,
                'avatar_url': await self.get_avatar_url(msg.user_id),
                'time': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'forwarded_messages': forwarded_messages,
            }
            messages_array.append(message_data)

        return messages_array

    async def chat_message(self, event):
        user_id = event['user_id']
        message = event['message']
        username = event.get('username', '')
        avatar_url = event.get('avatar_url', '')
        time = event.get('time', '')
        files = event.get('files', [])  # 获取files字段，如果没有则默认为空列表
        date = event.get('date', '')
        replyMessage = event.get('replyMessage', None)  #
        message_id = event.get('message_id', None)
        print(replyMessage)
        # 发送消息给 WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'team_id': self.team_id,
            'message_id': message_id,
            'user_id': user_id,
            'date': date,
            'message': message,
            'files': [files],
            'replyMessage': replyMessage,
            'username': username,
            'avatar_url': avatar_url,
            'time': time
        }))
    async def chat_forward_message(self, event):
        message = event['message']
        team_id = event['team_id']
        await self.send(text_data=json.dumps({
            'type': 'chat_forward_message',
            'team_id': team_id,
            'message': message,
        }))

    @database_sync_to_async
    def upload_chatmessage(self, message, user_id, replyMessage,date):
        ChatMessage.objects.create(team_id=self.team_id, message=message, user_id=user_id,
                                   reply_message=replyMessage, date=date)


    @database_sync_to_async
    def handle_files(self, file_data, message, user_id, replyMessage,date):
        if file_data:  # 检查是否真的拿到了文件数据
            file_instance = File(
                url=file_data['url'],
                name=file_data['name'],
                audio=file_data.get('audio', False),  # 使用get以处理可能的缺失字段
                duration=file_data.get('duration', 0),
                size=file_data.get('size', 0),
                preview=file_data.get('preview', None),
                type = file_data.get('type', None),
            )
            file_instance.save()
            print('拿到文件了')
            if file_instance:
                print('有文件')
                chat_message = ChatMessage.objects.create(team_id=self.team_id, message=message, user_id=user_id,
                                                          files=file_instance, reply_message=replyMessage,date=date)
                file_instance.chat_message = chat_message
                file_instance.save()
            print('保存文件成功')
        else:
            print('没有文件')
            # 假设你有一个名为ChatMessage的模型，用于存储消息
            ChatMessage.objects.create(team_id=self.team_id, message=message, user_id=user_id,
                                       reply_message=replyMessage,date=date)



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

    async def chat_delete_personal(self, event):
        deleter_id=event['deleter_id']
        await self.send(text_data=json.dumps({
            'type':'chat_delete_personal',
            'roomId':self.team_id,
            'deleter_id':deleter_id,
        }))

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
    def get_files(self, msg):
        if msg.files:
            file_data = [{
                'url': msg.files.url,
                'name': msg.files.name,
                'audio': msg.files.audio,
                'duration': msg.files.duration,
                'size': msg.files.size,
                'preview': msg.files.preview,
                'type': msg.files.type,
            }]
            return file_data
        else:
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
    def increment_unread_count_and_index_in_db(self, user_id):
        user_ids = ChatMember.objects.filter(team_id=self.team_id).values_list('user_id', flat=True)
        new_user_ids = user_ids.exclude(user_id=user_id)
        print(user_ids)
        print(new_user_ids)
        for uid in user_ids:
            status, created = UserTeamChatStatus.objects.get_or_create(user_id=uid, team_id=self.team_id,
                                                                       defaults={'unread_count': 0})
            print('status', status, 'created', created)
            if created:
                # 如果创建了新的记录, 设置unread_count为1
                if uid != user_id:
                    status.unread_count = 1
                print('创建了新的记录')
            else:
                # 否则增加unread_count
                print('进入index')
                if uid != user_id:
                    status.unread_count += 1

            # 获取最大index值
            max_index = UserTeamChatStatus.objects.filter(user_id=uid).aggregate(Max('index'))[
                                'index__max'] or 0
            print('max_index', max_index)


            # 设置index为最大值加1
            status.index = max_index + 1

            print('增加了unread_count')
            status.save()
        return user_ids

    @database_sync_to_async
    def increase_index(self, user_id, team_id):
        print('进入index')
        # 获取最大index值
        max_index = UserTeamChatStatus.objects.filter(user_id=user_id).aggregate(Max('index'))['index__max'] or 0
        print('max_index', max_index)
        # 使用get_or_create获取或创建对象
        user_team_chat_status, created = UserTeamChatStatus.objects.get_or_create(user_id=user_id, team_id=team_id)

        # 设置index为最大值加1
        user_team_chat_status.index = max_index + 1
        user_team_chat_status.save()

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
        print(user_ids_list)
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
    def forward_messages_as_combined(self, message_ids, replyMessage,group_id):
        # 获取所有要合并的消息
        messages = ChatMessage.objects.filter(id__in=message_ids)
        # 创建新的内容，可能包括每个原始消息的发送者、内容和头像

        # 获取当前日期
        now = datetime.now()

        # 获取日期的天和月份
        day = now.day
        month = now.strftime('%B')  # %B 是完整的月份名称

        # 格式化日期
        date = f"{day} {month}"
        # 创建新消息
        new_message = ChatMessage(user_id=self.user_id, message='群聊的聊天记录', is_forwarded=True, team_id=group_id,reply_message=replyMessage,date=date,files=None)
        new_message.save()

        # 添加被合并的消息到forwarded_from字段
        for message in messages:
            new_message.forwarded_from.add(message)
        print('合并消息成功',new_message)

        return new_message

    @database_sync_to_async
    def create_status(self, user_id, team_id):
        if UserTeamChatStatus.objects.filter(user_id=user_id, team_id=team_id).exists():
            return UserTeamChatStatus.objects.get(user_id=user_id, team_id=team_id)
        else:
            status = UserTeamChatStatus.objects.create(user_id=user_id, team_id=team_id, unread_count=0, index=0)
            return status



    async def notify(self, user_id):

        user_ids = await self.increment_unread_count_and_index_in_db(user_id)
        print('notify', user_ids)
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
    @database_sync_to_async
    def delete_user(self, user_id):
        UserChatChannel.objects.filter(user_id=user_id,team_id=self.team_id).delete()
        UserTeamChatStatus.objects.filter(user_id=user_id, team_id=self.team_id).delete()
        ChatMember.objects.filter(user_id=user_id, team_id=self.team_id).delete()
        print('删除用户成功')
    @database_sync_to_async
    def delete_group(self):
        UserChatChannel.objects.filter(team_id=self.team_id).delete()
        UserTeamChatStatus.objects.filter(team_id=self.team_id).delete()
        ChatMember.objects.filter(team_id=self.team_id).delete()
        ChatMessage.objects.filter(team_id=self.team_id).delete()
        Group.objects.filter(id=self.team_id).delete()
        print('删除团队成功')
    @database_sync_to_async
    def add_user(self, invitee_id):
        ChatMember.objects.create(user_id=invitee_id, team_id=self.team_id)
        UserTeamChatStatus.objects.create(user_id=invitee_id, team_id=self.team_id, unread_count=0, index=0)
        print('添加用户成功')
    @database_sync_to_async
    def get_latest_message_id(self):
        return ChatMessage.objects.filter(team_id=self.team_id).order_by('-timestamp').first().id
    @database_sync_to_async
    def to_dict(self, chatMessage):
        return chatMessage.to_dict(5) if chatMessage else None
    @database_sync_to_async
    def handle_foward_single(self, message_id, group_id):
        #获取message_ids中的每一个id，然后复制一遍，但修改其team_id为group_id存进数据库
        message=ChatMessage.objects.get(id=message_id)
        new_message=ChatMessage.objects.create(team_id=group_id, message=message.message, user_id=message.user_id,
                                   reply_message=message.reply_message, date=message.date,files=message.files)
        new_message.save()
        if message.files:
            new_message.files.chat_message=new_message
            new_message.files.save()
        new_message.save()
        return new_message








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
                roomID=data['roomID']
                # 广播消息给所有人
                await self.upload_all_chat_notice(data['url'], roomID)
            elif data['range'] == 'individual':
                # 发送消息给指定用户
                user_id = data['user_id']  # 假设传来的数据里有目标用户的ID
                url=data['url']
                roomID=data['roomID']
                notice_id=await self.upload_chat_notice(url, roomID, user_id)
                channel_name = await self.get_channel_name_for_user(user_id)
                if channel_name:
                # 用channel_name发送消息给指定用户
                    await self.channel_layer.send(channel_name, {
                        "type": "chat_notice",
                        "url": url,
                        "roomID": roomID,
                        "is_read": False,
                        "id":notice_id,
                    })

        elif data['type'] == 'file':
            user_id = data['user_id']  # 假设传来的数据里有目标用户的ID
            file_id = data['file_id']
            url=data['url']
            notice_id = await self.upload_file_notice(url, file_id, user_id)
            channel_name = await self.get_channel_name_for_user(user_id)
            if channel_name:
                # 用channel_name发送消息给指定用户
                await self.channel_layer.send(channel_name, {
                    "type": "file_notice",
                    "url": url,
                    "is_read": False,
                    "id": notice_id,
                })

    @database_sync_to_async
    def get_channel_name_for_user(self, user_id):
        if UserNoticeChannel.objects.filter(user_id=user_id).exists():
            channel = UserNoticeChannel.objects.get(user_id=user_id)
            return channel.channel_name
        else:
            return None

    @database_sync_to_async
    def upload_all_chat_notice(self, url,roomID):
        members=Member.objects.filter(team_id=roomID)

        for member in members:
            print(member.user_id)
            notice=Notice.objects.create(receiver_id=member.user_id, notice_type='chat_mention', url=url,
                                  associated_resource_id=roomID)
            try:
                channel_name = self.get_channel_name_for_user(member.user_id)
                async_to_sync(self.channel_layer.group_send)(channel_name, {
                    "type": "chat_notice",
                    "url": url,
                    "roomID": roomID,
                    "is_read": False,
                    "id":notice.id,
                })
            except:
                print('没有找到channel_name')



    async def chat_notice(self, event):
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'type': 'chat_notice',
            'url': event["url"],
            'roomID': event["roomID"],
            'is_read': event["is_read"],
            'id': event["id"],
        }))
    async def file_notice(self, event):
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'type': 'file_notice',
            'url': event["url"],
            'is_read': event["is_read"],
            'id': event["id"],
        }))

    async def new_group_chat(self, event):
        room = event['room']
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'type': 'new_group_chat',
            'room': room,
        }))
    async def chat_delete_all(self, event):
        roomID = event['roomID']
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'type': 'chat_delete_all',
            'roomID': roomID,
        }))
    async def send_notification(self, event):
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'message': event["message"]
        }))

    async def chat_add_members(self, event):
        # 实际发送消息给WebSocket客户端
        await self.send(text_data=json.dumps({
            'type': 'chat_add_members',
            'roomId': event["roomId"],
            'users': event["users"],
        }))
    @database_sync_to_async
    def save_user_notice_channel(self):
        UserNoticeChannel.objects.update_or_create(user_id=self.user_id, defaults={'channel_name': self.channel_name})
    @database_sync_to_async
    def upload_chat_notice(self, url, roomID,user_id):
        notice=Notice.objects.create(receiver_id=user_id, notice_type='chat_mention', url=url,
                              associated_resource_id=roomID)
        return notice.id
    @database_sync_to_async
    def upload_file_notice(self, url, file_id,user_id):
        notice=Notice.objects.create(receiver_id=user_id, notice_type='document_mention', url=url,
                              associated_resource_id=file_id)
        return notice.id



from .online_users import online_users

class DocumentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['document_id']
        self.user_id = int(self.scope['url_route']['kwargs']['user_id'])
        self.room_group_name = 'document_%s' % self.room_name

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # 初始化文档的在线用户列表
        if self.room_name not in online_users:
            online_users[self.room_name] = []

        if self.user_id not in online_users[self.room_name]:
            online_users[self.room_name].append(self.user_id)

        await self.send_updated_users()

    async def disconnect(self, close_code):
        if self.room_name in online_users and self.user_id in online_users[self.room_name]:
            online_users[self.room_name].remove(self.user_id)
            await self.send_updated_users()

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def send_updated_users(self):
        # 获取在线用户的ID列表
        online_user_ids = online_users.get(self.room_name, [])

        # 使用User模型查询用户ID和头像URL
        online_user_profiles = await self.get_online_user_profiles(online_user_ids)

        # 提取头像URL和用户ID的配对
        user_data = [{'id': user['id'], 'avatar_url': user['avatar_url']} for user in online_user_profiles]

        # 广播用户数据
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'users_update',
                'online_users': user_data
            }
        )

    @database_sync_to_async
    def get_online_user_profiles(self, online_user_ids):
        return list(User.objects.filter(id__in=online_user_ids).values('id', 'avatar_url'))

    async def users_update(self, event):
        await self.send(text_data=json.dumps(event))



