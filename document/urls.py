

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path('create_document/<int:project_id>/', views.create_document, name='create_document'),
    path('view_document/<str:token>/', views.view_document, name='create_document'),
    path('share_document/',views.share_document),
    path('change_lock/',views.change_lock),
    path('save_document/',views.save_document),
    path('all_documents/<int:project_id>/',views.all_documents),
    path('create_prototype/<int:project_id>/',views.create_prototype),
    path('save_prototype/',views.save_prototype),
    path('view_prototype/',views.view_prototype),
    path('all_prototype/<int:project_id>/',views.all_prototype),
    path('all_deleted_document/',views.all_deleted_document),
    path('recover_one_document/',views.recover_one_document),
    path('recover_all_document/',views.recover_all_document)
]