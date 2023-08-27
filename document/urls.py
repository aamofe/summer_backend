

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path('create_document/<int:team_id>/', views.create_document, name='create_document'),
    path('view_document/<str:token>/', views.view_document, name='create_document'),
    path('share_document/<int:team_id>/',views.share_document),
    path('change_lock/',views.change_lock),
    path('save_document/<int:team_id>/',views.save_document),
    # path('get_lock/<int:team_id>/',views.get_lock)
]