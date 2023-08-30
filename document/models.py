import pytz
from django.db import models

from team.models import Team, Project
from user.models import User

shanghai_tz = pytz.timezone('Asia/Shanghai')
# Create your models here.
class Document(models.Model):
    title=models.CharField(verbose_name="标题",max_length=20)
    content=models.TextField(verbose_name="文档内容",null=True)
    url=models.URLField(verbose_name="不可编辑文档链接",null=True)
    url_editable=models.URLField(verbose_name="可编辑链接",null=True)
    created_at=models.DateTimeField(verbose_name="创建时间",auto_now_add=True)
    modified_at=models.DateTimeField(verbose_name="最近修改时间",auto_now=True)
    # team=models.ForeignKey(Team,verbose_name="所属团队",on_delete=models.CASCADE)
    project=models.ForeignKey(Project,verbose_name="所属项目",on_delete=models.CASCADE)
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.CASCADE)
    is_locked=models.IntegerField(verbose_name="文件锁",default=False)
    is_deleted=models.BooleanField(verbose_name="是否被删除",default=False)
    def to_dict(self):

        return {
            'id':self.id,
            'title':self.title,
            'content':self.content,
            'creator':self.user.id,
            'created_at':(self.created_at.astimezone(shanghai_tz)).strftime('%Y-%m-%d %H:%M:%S'),
            'modified_at':(self.modified_at.astimezone(shanghai_tz)).strftime('%Y-%m-%d %H:%M:%S'),
            'is_locked':self.is_locked,
            'type':'document'
        }

class History(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="文档内容",null=True)
    modified_at = models.DateTimeField(verbose_name="修改时间", auto_now_add=True)
    class Meta:
        ordering = ['-modified_at']
    def to_dict(self):
        return {
            'content':self.content,
            'modified_at':self.modified_at,
        }
class Prototype(models.Model):
    title=models.CharField(verbose_name='标题',max_length=20)
    content=models.TextField(verbose_name='',default="")
    created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name="最近修改时间", auto_now=True)
    # team=models.ForeignKey(Team,verbose_name='原型所属团队',on_delete=models.CASCADE)
    project = models.ForeignKey(Project, verbose_name="所属项目", on_delete=models.CASCADE)
    user=models.ForeignKey(User,verbose_name="创建者",on_delete=models.CASCADE)
    is_deleted=models.BooleanField(verbose_name="是否已删除",default=False)
    visible=models.BooleanField(verbose_name='是否可见',default=True)
    token = models.URLField(verbose_name="预览原型链接", null=True)
    length =models.DecimalField(default=1920,max_digits=10, decimal_places=2)
    width = models.DecimalField(default=1080,max_digits=10, decimal_places=2)
    def to_dict(self):
        return {
            'id':self.id,
            'title':self.title,
            'content':self.content,
            'created_at':self.created_at,
            'modified_at':self.modified_at,
            'project_name':self.project.name,
            'creator':self.user.nickname,
            'type':'prototype'
        }

# class Template(models.Model):
#     title = models.CharField(verbose_name='标题', max_length=20)
#     content = models.TextField(verbose_name='', default="")
#     created_at = models.DateTimeField(verbose_name="创建时间", auto_now_add=True)
#     modified_at = models.DateTimeField(verbose_name="最近修改时间", auto_now=True)

class Folder(models.Model):
    name = models.CharField(max_length=50)
    parent_folder = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_folders')
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    def to_dict(self):
        children = []
        for child_folder in self.child_folders.all():
            children.append(child_folder.to_dict_recursive())  # 递归获取子文件夹信息
        for document in Document.objects.filter(folder=self):
            children.append(document.to_dict())
        return {
            'id': self.id,
            'name': self.name,
            'project_name': self.project.name,
            'parent_folder_id': self.parent_folder_id,
            'type': 'folder',
            'children': children  # 添加子文件夹和子文件信息
        }