import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import SessionMiddlewareStack
from django.core.asgi import get_asgi_application
from django.urls import path
from chat import consumers

websocket_urlpatterns = [
    path('<int:team_id>/chat/<int:user_id>', consumers.TeamChatConsumer.as_asgi()),
    path('notice/<int:user_id>', consumers.NotificationConsumer.as_asgi()),
    path('<int:document_id>/document/<int:user_id>', consumers.DocumentConsumer.as_asgi()),
    #path('<int:u1_id>/chat/<int:u2_id>/', consumers.PrivateChatConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": SessionMiddlewareStack(URLRouter(websocket_urlpatterns))
})

