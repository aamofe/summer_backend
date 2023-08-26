from django.urls import path

from chat import views

urlpatterns = [
    path('document/<int:team_id>/<int:user_id>', views.upload_image),
    path('initial/<int:user_id>',views.initial_chat),
]