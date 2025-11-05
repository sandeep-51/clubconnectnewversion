from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('create_user/', views.create_user_by_admin, name='create_user_by_admin'),
]