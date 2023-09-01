

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    # path('create_document/<int:project_id>/', views.create_document, name='create_document'),
    path('view_document/<str:token>/', views.view_document, name='create_document'),
    path('share_document/',views.share_document),
    path('change_lock/',views.change_lock),
    path('update_document_permisson/',views.update_document_permisson),
    # path('save_document/',views.save_document),
    # path('all_documents/<int:project_id>/',views.all_documents),
    # path('create_prototype/<int:project_id>/',views.create_prototype),
    # path('save_prototype/',views.save_prototype),
    path('view_prototype/<str:token>/',views.view_prototype),
    # path('all_prototype/<int:project_id>/',views.all_prototype),
    # path('all_deleted_document/',views.all_deleted_document),
    # path('restore_one_document/',views.restore_one_document),
    # path('recover_all_document/',views.recover_all_document),
    path('create/',views.create),
    path('delete/',views.delete),
    # path('restore/',views.restore),
    path('save/',views.save),
    # path('all_file/',views.all_file),
    path('all_deleted/',views.all_deleted),
    path('history/',views.history),
    path('share_prototype/',views.share_prototype),
    path('create_folder/',views.create_folder),
    # path('delete_folder/',views.delete_folder),
    path('view_folder/',views.view_folder),
    path('restore/',views.restore),
    # path('rename_folder/',views.rename_folder),
    path('upload/',views.upload),
    path('delete_permanently/',views.delete_permanently),
    path('create_template_public/',views.create_template),
    path('save_as_template/',views.save_as_template),
    path('all_template/',views.all_template),
    path('import_from_template/',views.import_from_template),
    path('get_token/',views.get_token)
]