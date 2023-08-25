from django.db import models

# Create your models here.
class ChatMessage(models.Model):
    message = models.TextField()
    team_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

