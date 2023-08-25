import json

import jwt
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
from jose import JWTError
from jwt import ExpiredSignatureError

from chat.models import ChatMessage
from summer_backend import settings
from user.authentication import validate_login


# 假设您已经定义了此模型
# from .models import ChatMessage

class TeamChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_group_name = None
    async def connect(self):
        self.user_id = 1
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.room_group_name = f"chat_{self.team_id}"
        # 将用户加入到团队群聊
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        # authorization_headers = self.scope.get('headers', [])
        # authorization_header = next((header for header in authorization_headers if header[0].decode('utf-8').lower() == 'authorization'), None)
        # if authorization_header:
        #     token = authorization_header[1].decode('utf-8').replace('Bearer ', '')
        #     try:
        #         jwt_token = jwt.decode(token, settings.SECRET_KEY, options={'verify_signature': False})
        #         self.user_id = jwt_token.get('id')
        #         # 如果验证成功，则将用户加入到团队群聊
        #         self.team_id = self.scope['url_route']['kwargs']['team_id']
        #         self.room_group_name = f"chat_{self.team_id}"
        #         await self.channel_layer.group_add(
        #             self.room_group_name,
        #             self.channel_name
        #         )
        #         await self.accept()
        #     except ExpiredSignatureError:
        #         # 处理过期的 Token，阻止连接和消息发送
        #         await self.close()
        #     except JWTError:
        #         # 处理无效的 Token，阻止连接和消息发送
        #         await self.close()
        # else:
        #     # 处理没有 Authorization 头信息的情况，阻止连接和消息发送
        #     await self.close()

    async def disconnect(self, close_code):
        # 将用户从团队群聊中移除
        print("11112")
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        print("11113")
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
        print("11114")
        message = event['message']

        # 发送消息给 WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    @database_sync_to_async
    def save_message(self, message):
        print("11115")
        # 假设你有一个名为ChatMessage的模型，用于存储消息
        ChatMessage.objects.create(team_id=self.team_id, message=message,user_id=self.user_id)

    @database_sync_to_async
    def search_messages(self, keyword):
        print("11116")
        # 搜索包含关键字的消息
        messages = ChatMessage.objects.filter(team_id=self.team_id, message__icontains=keyword)
        return [msg.message for msg in messages]
