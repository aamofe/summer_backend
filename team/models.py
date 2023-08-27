from django.db import models
from user.models import User
# Create your models here.
class Team(models.Model):
    name=models.CharField(verbose_name="团队名称",max_length=10,default='未命名团队')
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.CASCADE)
    description=models.CharField(verbose_name="团队描述", max_length=10, null=True)
    created_at = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    cover_url=models.URLField(verbose_name="团队封面",default="https://summer-1315620690.cos.ap-beijing.myqcloud.com/team_cover/default.png")
    invitation=models.URLField(verbose_name='邀请链接',null=True)
    # is_deleted=models.BooleanField(verbose_name="是否删除",default=False)
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at':self.created_at,
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
    user=models.ForeignKey(User,verbose_name="成员",on_delete=models.PROTECT)
    team=models.ForeignKey(Team,on_delete=models.PROTECT)
    def __str__(self):
        return f"{self.get_role_display()}"
class Project(models.Model):
    name=models.CharField(verbose_name='项目名称',max_length=10)
    created_at=models.DateTimeField(verbose_name='项目创建时间',auto_now_add=True)
    team=models.ForeignKey(Team,verbose_name="所属团队",on_delete=models.PROTECT)
    is_deleted = models.BooleanField(verbose_name='是否已删除', default=False)
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.PROTECT)
    def to_dict(self):
        return{
            'name':self.name,
            'id':self.id,
        }