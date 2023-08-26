

from django.urls import path

from . import views
from .views import *

urlpatterns = [
    path('create_document/<int:team_id>/', views.create_document, name='create_document'),
    path('view_document/<int:document_id>/', views.view_document, name='create_document'),

]