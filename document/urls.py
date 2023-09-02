

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path('view_document/<str:token>/', views.view_document, name='create_document'),
    path('share_document/',views.share_document),
    path('update_document_permisson/',views.update_document_permisson),
    path('view_prototype/<str:token>/',views.view_prototype),
    path('create/',views.create),
    path('delete/',views.delete),
    path('restore/',views.restore),
    path('save/',views.save),
    path('all_deleted/',views.all_deleted),
    path('history/',views.history),
    path('share_prototype/',views.share_prototype),
    path('create_folder/',views.create_folder),
    path('view_folder/',views.view_folder),
    path('upload/',views.upload),
    path('delete_permanently/',views.delete_permanently),
    path('save_as_template/',views.save_as_template),
    path('all_template/',views.all_template),
    path('import_from_template/',views.import_from_template),
    path('get_token/',views.get_token)
]