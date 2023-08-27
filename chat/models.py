from django.db import models

from team.models import Team
from user.models import User


# Create your models here.
class ChatMessage(models.Model):
    message = models.TextField(default=None)
    reply_message = models.TextField(default=None)
    files = models.TextField(default=None)
    team_id = models.IntegerField()
    user_id = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)


class Notice(models.Model):
    TYPE_CHOICES = [
        ('chat_mention', 'Chat Mention'),
        ('document_mention', 'Document Mention'),
        # 其他通知类型可以继续在这里添加
    ]
    receiver = models.ForeignKey(User, on_delete=models.CASCADE)
    notice_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    content = models.TextField()
    associated_resource_id = models.IntegerField()
    position_info = models.TextField(blank=True, null=True)  # 可以存储JSON格式的位置信息
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

class UserTeamChatStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    unread_count = models.PositiveIntegerField(default=0)
    is_at = models.BooleanField(default=False)
    is_at_all = models.BooleanField(default=False)
    index = models.IntegerField(default=0)


class UserChatChannel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    channel_name = models.CharField(max_length=255, unique=True)


class UserNoticeChannel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel_name = models.CharField(max_length=255, unique=True)


