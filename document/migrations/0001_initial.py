# Generated by Django 3.2.5 on 2023-08-31 02:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('team', '0004_alter_member_user_alter_team_user'),
        ('user', '0004_auto_20230830_1912'),
    ]

    operations = [
        migrations.CreateModel(
            name='Document',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=20, verbose_name='标题')),
                ('content', models.TextField(null=True, verbose_name='文档内容')),
                ('url', models.URLField(null=True, verbose_name='不可编辑文档链接')),
                ('url_editable', models.URLField(null=True, verbose_name='可编辑链接')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='最近修改时间')),
                ('deleted_at', models.DateTimeField(null=True, verbose_name='被删除时间')),
                ('is_locked', models.IntegerField(default=False, verbose_name='文件锁')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否被删除')),
            ],
        ),
        migrations.CreateModel(
            name='Folder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('deleted_at', models.DateTimeField(null=True, verbose_name='被删除时间')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否被删除')),
                ('parent_folder', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='child_folders', to='document.folder')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='team.project')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.user')),
            ],
        ),
        migrations.CreateModel(
            name='Prototype',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=20, verbose_name='标题')),
                ('content', models.TextField(default='', verbose_name='')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('modified_at', models.DateTimeField(auto_now=True, verbose_name='最近修改时间')),
                ('deleted_at', models.DateTimeField(null=True, verbose_name='被删除时间')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='是否已删除')),
                ('visible', models.BooleanField(default=True, verbose_name='是否可见')),
                ('token', models.URLField(null=True, verbose_name='预览原型链接')),
                ('height', models.DecimalField(decimal_places=2, default=1080, max_digits=10)),
                ('width', models.DecimalField(decimal_places=2, default=1920, max_digits=10)),
                ('parent_folder', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='document.folder', verbose_name='所属文件夹')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.user', verbose_name='创建者')),
            ],
        ),
        migrations.CreateModel(
            name='History',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(null=True, verbose_name='文档内容')),
                ('modified_at', models.DateTimeField(auto_now_add=True, verbose_name='修改时间')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='document.document')),
            ],
            options={
                'ordering': ['-modified_at'],
            },
        ),
        migrations.AddField(
            model_name='document',
            name='parent_folder',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='document.folder', verbose_name='所属文件夹'),
        ),
        migrations.AddField(
            model_name='document',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='user.user', verbose_name='创建者'),
        ),
        migrations.CreateModel(
            name='Copy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('original', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='original_copies', to='document.folder')),
                ('revised', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revised_copies', to='document.folder')),
            ],
        ),
    ]
