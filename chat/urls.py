from django.urls import path

from chat import views

urlpatterns = [
    #path('document/<int:team_id>/', views.upload_document),
    path('initial/<int:user_id>',views.initial_chat),
]