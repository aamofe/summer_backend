from django.urls import path

from chat import views

urlpatterns = [
    path('document/<int:team_id>/<int:user_id>', views.upload_image),
    path('initial/<int:user_id>',views.initial_chat),
    path('<int:user_id>',views.get_user_messages),

    path('notice/make_read/<int:notice_id>',views.make_notice_read),
    path('notice/make_unread/<int:notice_id>',views.make_notice_unread),

    path('<int:user_id>/unread',views.get_unread_messages),
    path('notice/all_as_read/<int:user_id>',views.mark_all_as_read),
    path('notice/delete/<int:notice_id>',views.delete_notice),
    path('notice/delete_all_read/<int:user_id>',views.delete_all_read),

    path('get_group_id/<int:user_id>/<int:team_id>',views.get_group_id),
    path('get_group_members/<int:group_id>',views.get_group_members),

]