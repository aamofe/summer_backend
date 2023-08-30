# Generated by Django 3.2.5 on 2023-08-30 03:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0003_alter_user_avatar_url'),
        ('team', '0002_auto_20230829_1338'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='is_real',
            field=models.BooleanField(default=True, verbose_name='是否为真是群聊'),
        ),
        migrations.AlterField(
            model_name='member',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='team.team'),
        ),
        migrations.AlterField(
            model_name='member',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.user', verbose_name='成员'),
        ),
        migrations.AlterField(
            model_name='project',
            name='team',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='team.team', verbose_name='所属团队'),
        ),
        migrations.AlterField(
            model_name='project',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.user', verbose_name='创建者'),
        ),
    ]