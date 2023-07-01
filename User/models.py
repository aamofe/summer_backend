from django.db import models

# Create your models here.
from django.db import models

# Create your models here.
class User(models.Model):
    username=models.CharField(verbose_name="用户名",max_length=10)
    email=models.EmailField(verbose_name="邮箱")
    #密码要求是 数字+字母 8-16位
    password=models.CharField(verbose_name="账户密码",max_length=16)
    avatar_url = models.CharField('头像地址',max_length=128,default='')
    description=models.CharField('签名',max_length=128,default='')
    created_at=models.DateTimeField('注册时间',auto_now_add=True)
    isActive=models.BooleanField('是否有效账户',max_length=10,default=False)
    def to_dict(self):
        return {
            'id':self.id,
            'email':self.email,
        }