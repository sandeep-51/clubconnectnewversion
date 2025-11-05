from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('student', 'Student'),
        ('founder', 'Founder'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    current_session_key = models.CharField(max_length=40, blank=True, null=True)
    
    def is_online(self):
        if self.last_seen:
            return (timezone.now() - self.last_seen) < timezone.timedelta(minutes=5)
        return False

    def is_admin(self):
        return self.user_type == 'admin'
    
    def is_student(self):
        return self.user_type == 'student'
    
    def is_founder(self):
        return self.user_type == 'founder'
