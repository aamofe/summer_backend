from django.db import models

from team.models import Team, Project
from user.models import User


# Create your models here.
class Document(models.Model):
    title=models.CharField(verbose_name="标题",max_length=20)
    content=models.TextField(verbose_name="文档内容")
    url=models.URLField(verbose_name="不可编辑文档链接",null=True)
    url_editable=models.URLField(verbose_name="可编辑链接",null=True)
    created_at=models.DateTimeField(verbose_name="创建时间",auto_now_add=True)
    modified_at=models.DateTimeField(verbose_name="最近修改时间",auto_now=True)
    # team=models.ForeignKey(Team,verbose_name="所属团队",on_delete=models.PROTECT)
    project=models.ForeignKey(Project,verbose_name="所属项目",on_delete=models.PROTECT)
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.PROTECT)
    is_locked=models.IntegerField(verbose_name="文件锁",default=False)
    is_deleted=models.BooleanField(verbose_name="是否被删除",default=False)
    def to_dict(self):
        return {
            'id':self.id,
            'title':self.title,
            'content':self.content,
            'creator':self.user.id,
            'created_at':self.created_at,
            'modified_at':self.modified_at,
            'is_locked':self.is_locked
        }


class Prototype(models.Model):
    title=models.CharField(verbose_name='标题',max_length=20)
    content=models.TextField(verbose_name='',default="")
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name="最近修改时间", auto_now=True)
    # team=models.ForeignKey(Team,verbose_name='原型所属团队',on_delete=models.PROTECT)
    project = models.ForeignKey(Project, verbose_name="所属项目", on_delete=models.PROTECT)
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.PROTECT)
    is_deleted=models.BooleanField(verbose_name="是否已删除",default=False)
    def to_dict(self):
        return {
            'id':self.id,
            'title':self.title,
            'content':self.content,
            'created_at':self.created_at,
            'modified_at':self.modified_at,
            'project_name':self.project.name,
            'creator':self.user.nickname,
        }