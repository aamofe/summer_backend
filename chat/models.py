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
    user_id = models.IntegerField()
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

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


