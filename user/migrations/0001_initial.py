# Generated by Django 3.2.5 on 2023-08-27 15:40

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=20, verbose_name='消息标题')),
                ('content', models.CharField(max_length=100, verbose_name='消息具体内容')),
                ('url', models.URLField(verbose_name='跳转链接')),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=10, verbose_name='真实姓名')),
                ('nickname', models.CharField(max_length=10, verbose_name='昵称')),
                ('email', models.EmailField(max_length=254, verbose_name='邮箱')),
                ('password', models.CharField(max_length=16, verbose_name='账户密码')),
                ('avatar_url', models.URLField(default='https://summer-1315620690.cos.ap-beijing.myqcloud.com/avatar/default.png', verbose_name='头像路径')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='注册时间')),
                ('is_active', models.BooleanField(default=False, max_length=10, verbose_name='是否有效账户')),
                ('current_team_id', models.IntegerField(verbose_name='当前团队id')),
            ],
        ),
    ]
