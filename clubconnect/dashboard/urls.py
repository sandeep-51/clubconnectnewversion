from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    
    path('chat/', views.chat_view, name='chat'),
    path('ajax/messages/<int:user_id>/', views.get_messages, name='get_messages'),
    path('ajax/send_message/', views.send_message, name='send_message'),
    path('ajax/edit_message/<int:message_id>/', views.edit_message, name='edit_message'),
    path('ajax/unsend_message/<int:message_id>/', views.unsend_message, name='unsend_message'),
    path('ajax/mark_messages_as_read/<int:user_id>/', views.mark_messages_as_read, name='mark_messages_as_read'),
    path('ajax/unread_messages_count/', views.unread_messages_count, name='unread_messages_count'),
    path('my_week/', views.my_week, name='my_week'),
    path('search/', views.search, name='search'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('ajax/unread_notifications_count/', views.get_unread_notifications_count, name='get_unread_notifications_count'),
    path('ajax/admin_analytics/', views.admin_analytics_data, name='admin_analytics_data'),
    path('activity-feed/', views.activity_feed, name='activity_feed'),
    path('my-clubs/', views.my_clubs, name='my_clubs'),
    path('home/', views.dashboard, name='home'),
    path('manage-users/', views.manage_users, name='manage_users'),
    path('manage-clubs/', views.manage_clubs, name='manage_clubs'),
    path('manage-settings/', views.manage_settings, name='manage_settings'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('events/', views.events, name='events'),
    path('profile/', views.profile, name='profile'),
    path('create-announcement/', views.create_announcement, name='create_announcement'),
    path('announcement/<int:announcement_id>/delete/', views.delete_announcement, name='delete_announcement'),
    path('reset-password/<int:user_id>/', views.reset_user_password, name='reset_user_password'),
    path('club-meetings/', views.student_club_meetings, name='student_club_meetings'),
]