from django.db import models

from user.models import User


# Create your models here.
class ChatMessage(models.Model):
    message = models.TextField(default=None)
    reply_message = models.TextField(default=None)
    files = models.ForeignKey('File', on_delete=models.CASCADE, blank=True, null=True)
    team_id = models.IntegerField()
    user_id = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    date = models.TextField(default=None, blank=True, null=True)
    forwarded_from = models.ManyToManyField("self", blank=True)


class Notice(models.Model):
    TYPE_CHOICES = [
        ('chat_mention', 'Chat Mention'),
        ('document_mention', 'Document Mention'),
        # 其他通知类型可以继续在这里添加
    ]
    receiver = models.ForeignKey(User, on_delete=models.CASCADE)
    notice_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    content = models.TextField(default=None, blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)
    associated_resource_id = models.IntegerField()
    position_info = models.TextField(blank=True, null=True)  # 可以存储JSON格式的位置信息
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

class UserTeamChatStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey('Group', on_delete=models.CASCADE)
    unread_count = models.PositiveIntegerField(default=0)
    is_at = models.BooleanField(default=False)
    is_at_all = models.BooleanField(default=False)
    index = models.IntegerField(default=0)


class UserChatChannel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    team = models.ForeignKey('Group', on_delete=models.CASCADE)
    channel_name = models.CharField(max_length=255, unique=True)


class UserNoticeChannel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    channel_name = models.CharField(max_length=255, unique=True)



class Group(models.Model):
    Chat_Choices=(
        ('team','团队'),
        ('group','群聊'),
        ('private','私聊')
    )
    name=models.CharField(verbose_name="团队名称",max_length=20,default='未命名团队')
    actual_team=models.IntegerField(blank=True,null=True)
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.CASCADE,related_name="chat_team_user")
    description=models.CharField(verbose_name="团队描述", max_length=50, null=True)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    cover_url=models.URLField(verbose_name="团队封面",default="https://summer-1315620690.cos.ap-beijing.myqcloud.com/team_cover/default.png")
    type=models.CharField(verbose_name="团队类型",choices=Chat_Choices,max_length=10,default='team')
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at':self.created_at,
            'creator':self.user.username,
        }
class ChatMember(models.Model):
    CREATOR = 'CR'
    MANAGER = 'MG'
    MEMBER = 'MB'
    ROLE_CHOICES = (
        (CREATOR, '创建者'),
        (MANAGER, '管理者'),
        (MEMBER, '普通成员'),
    )
    role = models.CharField(max_length=2,choices=ROLE_CHOICES,default=MEMBER,)
    user=models.ForeignKey(User,verbose_name="成员",on_delete=models.CASCADE,related_name="chat_member_user")
    team=models.ForeignKey('Group',on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.get_role_display()}"
class File(models.Model):
    chat_message=models.ForeignKey(ChatMessage,on_delete=models.CASCADE,blank=True,null=True)
    url=models.URLField(verbose_name="文件地址")
    name=models.CharField(verbose_name="文件名",max_length=50)
    audio=models.BooleanField(verbose_name="是否为音频",default=False)
    duration=models.IntegerField(verbose_name="音频时长",default=0)
    size=models.IntegerField(verbose_name="文件大小",default=0)
    preview=models.URLField(verbose_name="文件预览地址",default=None,null=True)



