import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async

from chat.models import ChatMessage


# 假设您已经定义了此模型
# from .models import ChatMessage

class TeamChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.room_group_name = f"chat_{self.team_id}"

        # 将用户加入到团队群聊
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # 将用户从团队群聊中移除
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)

        # 检查是否是搜索请求
        if 'search' in text_data_json:
            keyword = text_data_json['search']
            search_results = await self.search_messages(keyword)
            await self.send(text_data=json.dumps({
                'search_results': search_results
            }))
            return

        message = text_data_json['message']
        await self.save_message(message)

        # 将消息发送给团队群聊的所有成员
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def chat_message(self, event):
        message = event['message']

        # 发送消息给 WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    @database_sync_to_async
    def save_message(self, message):
        # 假设你有一个名为ChatMessage的模型，用于存储消息
        ChatMessage.objects.create(team_id=self.team_id, message=message)

    @database_sync_to_async
    def search_messages(self, keyword):
        # 搜索包含关键字的消息
        messages = ChatMessage.objects.filter(team_id=self.team_id, message__icontains=keyword)
        return [msg.message for msg in messages]
