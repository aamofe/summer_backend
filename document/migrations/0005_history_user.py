# Generated by Django 4.2.4 on 2023-08-31 14:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user', '0004_auto_20230830_1912'),
        ('document', '0004_remove_document_url_remove_document_url_editable_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='history',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='user.user', verbose_name='修改用户'),
            preserve_default=False,
        ),
    ]