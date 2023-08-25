

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path('create_team/', views.create_team, name='create_team'),
    path('get_invitation/', views.get_invitation, name='get_invitation'),
    path('accept_invitation/<str:token>/', views.accept_invitation, name='accept_invitation'),
    path('all_teams/', views.get_teams, name='get_teams'),
    path('all_members/', views.get_members, name='get_members'),
    path('update_permisson/<str:team_id>/',views.update_permisson),
]