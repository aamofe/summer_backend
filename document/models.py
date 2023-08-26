from django.db import models

from team.models import Team
from user.models import User


# Create your models here.
class Document(models.Model):
    title=models.CharField(verbose_name="标题",max_length=20)
    content=models.TextField(verbose_name="文档内容")
    url=models.URLField(verbose_name="不可编辑文档链接",null=True)
    url_editable=models.URLField(verbose_name="可编辑链接",null=True)
    created_at=models.DateTimeField(verbose_name="创建时间",auto_now_add=True)
    modified_at=models.DateTimeField(verbose_name="最近修改时间",auto_now=True)
    team=models.ForeignKey(Team,verbose_name="所属团队",on_delete=models.PROTECT)
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.PROTECT)
    isLocked=models.BooleanField(verbose_name="是否上锁",default=False)
    def to_dict(self):
        return {
            'title':self.title,
            'content':self.content,
            'creator':self.user.id,
            'created_at':self.created_at,
            'modified_at':self.modified_at
        }
