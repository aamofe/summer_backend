# Generated by Django 4.2.4 on 2023-08-26 20:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='current_team_id',
            field=models.IntegerField(default=0, verbose_name='当前团队id'),
            preserve_default=False,
        ),
    ]