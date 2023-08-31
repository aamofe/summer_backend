# Generated by Django 4.2.4 on 2023-08-31 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='is_private',
        ),
        migrations.AddField(
            model_name='group',
            name='type',
            field=models.CharField(choices=[('team', '团队'), ('group', '群聊'), ('private', '私聊')], default='team', max_length=10, verbose_name='团队类型'),
        ),
    ]
