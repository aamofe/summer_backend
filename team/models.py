import pytz
from django.db import models

from user.models import User
shanghai_tz = pytz.timezone('Asia/Shanghai')
# Create your models here.
class Team(models.Model):
    name=models.CharField(verbose_name="团队名称",max_length=20,default='未命名团队')
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.CASCADE,related_name="team_member_user")
    description=models.CharField(verbose_name="团队描述", max_length=50, null=True)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    cover_url=models.URLField(verbose_name="团队封面",default="https://summer-1315620690.cos.ap-beijing.myqcloud.com/team_cover/default.png")
    # is_real=models.BooleanField(verbose_name='是否为真是群聊',default=True)
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at':(self.created_at.astimezone(shanghai_tz)).strftime('%Y-%m-%d %H:%M:%S'),
            'creator':self.user.username,
        }
class Member(models.Model):
    CREATOR = 'CR'
    MANAGER = 'MG'
    MEMBER = 'MB'
    ROLE_CHOICES = (
        (CREATOR, '创建者'),
        (MANAGER, '管理者'),
        (MEMBER, '普通成员'),
    )
    role = models.CharField(max_length=2,choices=ROLE_CHOICES,default=MEMBER,)
    user=models.ForeignKey(User,verbose_name="成员",on_delete=models.CASCADE,related_name="team_team_user")
    team=models.ForeignKey(Team,on_delete=models.CASCADE)
    def __str__(self):
        return f"{self.get_role_display()}"
class Project(models.Model):
    name=models.CharField(verbose_name='项目名称',max_length=20)
    created_at=models.DateTimeField(verbose_name='项目创建时间',auto_now_add=True)
    team=models.ForeignKey(Team,verbose_name="所属团队",on_delete=models.CASCADE)
    is_deleted = models.BooleanField(verbose_name='是否已删除', default=False)
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.CASCADE)
    deleted_at=models.DateTimeField(verbose_name='被删除时间',null=True)
    def to_dict(self):
        return{
            'name':self.name,
            'id':self.id,
        }