from django.urls import path
from . import views

urlpatterns = [
    path('', views.clubs_list, name='clubs_list'),
    path('create/', views.create_club, name='create_club'),
    path('<int:club_id>/assign-founder/', views.assign_founder, name='assign_founder'),
    path('<int:club_id>/', views.club_detail, name='club_detail'),
    path('<int:club_id>/edit/', views.edit_club, name='edit_club'),
    path('search/', views.search_clubs, name='search_clubs'),
    path('<int:club_id>/register/', views.register_for_club, name='register_for_club'),
    path('<int:club_id>/message-founder/', views.send_message_to_founder, name='message_founder'),
    path('<int:club_id>/create-event/', views.create_event, name='create_event'),
    path('<int:club_id>/chat/', views.club_chat, name='club_chat'),
    path('membership/<int:membership_id>/approve/', views.approve_membership, name='approve_membership'),
    path('<int:club_id>/leave/', views.leave_club, name='leave_club'),
    path('membership/<int:membership_id>/reject/', views.reject_membership, name='reject_membership'),
    path('<int:club_id>/create-announcement/', views.create_club_announcement, name='create_club_announcement'),
    path('announcement/<int:announcement_id>/delete/', views.delete_club_announcement, name='delete_club_announcement'),
    
    path('event/<int:event_id>/generate-qr/', views.generate_event_qr, name='generate_event_qr'),
    path('event/<int:event_id>/checkin/', views.event_checkin, name='event_checkin'),
    path('event/<int:event_id>/register/', views.event_register, name='event_register'),
    path('event/<int:event_id>/download-qr/', views.download_event_qr, name='download_event_qr'),
    path('event/<int:event_id>/manage-attendance/', views.manage_event_attendance, name='manage_event_attendance'),
    
    path('<int:club_id>/create-survey/', views.create_survey, name='create_survey'),
    path('survey/<int:survey_id>/', views.view_survey, name='view_survey'),
    path('survey/<int:survey_id>/results/', views.survey_results, name='survey_results'),
    
    path('<int:club_id>/create-post/', views.create_club_post, name='create_club_post'),
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),
    
    path('<int:club_id>/leaderboard/', views.club_leaderboard, name='club_leaderboard'),
    
    path('<int:club_id>/toggle-favorite/', views.toggle_favorite_club, name='toggle_favorite_club'),
    
    path('<int:club_id>/submit-feedback/', views.submit_club_feedback, name='submit_club_feedback'),
    path('<int:club_id>/feedback/', views.view_club_feedbacks, name='view_club_feedbacks'),
    path('feedback/<int:feedback_id>/update/', views.update_feedback_status, name='update_feedback_status'),
    
    path('<int:club_id>/book-mentor/', views.book_mentor_session, name='book_mentor_session'),
    path('<int:club_id>/mentor-sessions/', views.view_mentor_sessions, name='view_mentor_sessions'),
    path('mentor-session/<int:session_id>/update/', views.update_mentor_session, name='update_mentor_session'),
    
    path('<int:club_id>/create-meeting/', views.create_club_meeting, name='create_club_meeting'),
    path('<int:club_id>/meeting/<str:meeting_link>/', views.join_club_meeting, name='join_club_meeting'),
    path('meeting/<int:meeting_id>/start/', views.start_club_meeting, name='start_club_meeting'),
    path('meeting/<int:meeting_id>/end/', views.end_club_meeting, name='end_club_meeting'),
    
    path('meeting/webrtc/signal/', views.send_webrtc_signal, name='send_webrtc_signal'),
    path('meeting/<int:meeting_id>/webrtc/signals/', views.get_webrtc_signals, name='get_webrtc_signals'),
]