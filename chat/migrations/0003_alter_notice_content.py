# Generated by Django 4.2.4 on 2023-08-27 19:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_notice_url_alter_notice_content'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notice',
            name='content',
            field=models.TextField(blank=True, default=None, null=True),
        ),
    ]