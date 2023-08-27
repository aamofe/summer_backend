

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path('create_team/', views.create_team, name='create_team'),
    path('update_team/',views.update_team),
    path('checkout_team/',views.checkout_team),
    path('get_current_team/',views.get_current_team),
    path('get_invitation/', views.get_invitation, name='get_invitation'),
    path('open_invitation/<str:token>/',views.open_invitation,name='open_invitation'),
    path('accept_invitation/', views.accept_invitation, name='accept_invitation'),
    path('all_teams/', views.all_teams, name='get_teams'),
    path('all_members/', views.all_members, name='get_members'),
    path('update_permisson/<str:team_id>/',views.update_permisson),
    # path('redi/',views.redi)
    path('create_project/<int:team_id>/',views.create_project),
    path('update_project/',views.update_project),
    path('rename_project/',views.rename_project),
    path('all_projects/',views.all_projects),
    path('get_one_team/',views.get_one_team)
]