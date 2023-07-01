

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path('register',register),
    path('activate/<str:token>/', views.activate, name='activate'),
]