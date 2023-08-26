# Generated by Django 4.2.4 on 2023-08-26 06:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('user', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='未命名团队', max_length=10, verbose_name='团队名称')),
                ('description', models.CharField(max_length=10, null=True, verbose_name='团队描述')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('cover_url', models.URLField(verbose_name='团队封面')),
                ('invitation', models.URLField(null=True, verbose_name='邀请链接')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.user', verbose_name='创建者')),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_created=True, verbose_name='项目创建时间')),
                ('name', models.CharField(max_length=10, verbose_name='项目名称')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否已删除')),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='team.team', verbose_name='所属团队')),
            ],
        ),
        migrations.CreateModel(
            name='Member',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('CR', '创建者'), ('MG', '管理者'), ('MB', '普通成员')], default='MB', max_length=2)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='team.team')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='user.user', verbose_name='成员')),
            ],
        ),
    ]
