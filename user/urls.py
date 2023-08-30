

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path('register/',register),
    path('activate/<str:token>/', views.activate, name='activate'),
    path('login/',views.login),
    path('logout/',views.logout),
    path('update_info/',views.update_info),
    path('show_info/<int:id>/', views.show_info),
    path('logout1/',views.logout1)
    # path('personal_info/',views.personal_info)
]