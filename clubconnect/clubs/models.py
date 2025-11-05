from django.db import models
from django.conf import settings

class Club(models.Model):
    name = models.CharField(max_length=100)
    short_description = models.CharField(max_length=200)
    long_description = models.TextField()
    domain_tags = models.CharField(max_length=200, help_text="Comma separated tags")
    founders = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='founded_clubs')
    president = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='club_president')
    vice_president = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='club_vice_president')
    faculty_advisor = models.CharField(max_length=100, blank=True)
    logo = models.ImageField(upload_to='club_logos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorite_clubs', blank=True)
    
    def __str__(self):
        return self.name
    
    def get_representatives(self):
        reps = list(self.founders.all())
        if self.president:
            reps.append(self.president)
        if self.vice_president:
            reps.append(self.vice_president)
        return list(set(reps))

class Event(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    qr_code = models.ImageField(upload_to='event_qr_codes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    def get_qr_code_url(self):
        from django.urls import reverse
        return reverse('event_checkin', kwargs={'event_id': self.id})

class Membership(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'club')
    
    def __str__(self):
        return f"{self.user.username} - {self.club.name}"

class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username}"

class Announcement(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='announcements', null=True, blank=True)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('announcement', 'Announcement'),
        ('event', 'Event'),
        ('membership', 'Membership'),
        ('message', 'Message'),
        ('general', 'General'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class ClubPost(models.Model):
    POST_TYPES = (
        ('event', 'Event'),
        ('info', 'Information'),
        ('meme', 'Meme'),
        ('general', 'General'),
    )
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='general')
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='club_posts/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_posts', blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.club.name} - {self.title}"
    
    def total_likes(self):
        return self.likes.count()

class MemberPoints(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='member_points')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='member_points')
    points = models.IntegerField(default=0)
    participation_count = models.IntegerField(default=0)
    contribution_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('user', 'club')
        ordering = ['-points']
    
    def __str__(self):
        return f"{self.user.username} - {self.club.name}: {self.points} pts"

class Survey(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='surveys')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title

class SurveyQuestion(models.Model):
    QUESTION_TYPES = (
        ('text', 'Text'),
        ('choice', 'Multiple Choice'),
        ('rating', 'Rating (1-5)'),
    )
    
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES)
    choices = models.TextField(blank=True, help_text="Comma separated choices for multiple choice")
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.question_text

class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('survey', 'user', 'question')
    
    def __str__(self):
        return f"{self.user.username} - {self.survey.title}"

class EventAttendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    checked_in_at = models.DateTimeField(auto_now_add=True)
    checked_in_via_qr = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('event', 'user')
    
    def __str__(self):
        return f"{self.user.username} - {self.event.title}"

class ClubFeedback(models.Model):
    FEEDBACK_TYPES = (
        ('feedback', 'General Feedback'),
        ('event_idea', 'Event Idea'),
        ('suggestion', 'Suggestion'),
    )
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='feedbacks')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES, default='feedback')
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('reviewed', 'Reviewed'), ('implemented', 'Implemented')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_feedbacks')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.title}"

class MentorSession(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    )
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='mentor_sessions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mentor_requests')
    mentor_topic = models.CharField(max_length=200)
    description = models.TextField()
    preferred_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    assigned_mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='mentoring_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    meeting_link = models.CharField(max_length=500, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.student.username} - {self.mentor_topic}"

class ClubMeeting(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('started', 'Started'),
        ('ended', 'Ended'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='meetings')
    title = models.CharField(max_length=200)
    description = models.TextField()
    scheduled_time = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    meeting_link = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    started_at = models.DateTimeField(null=True, blank=True)
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='started_meetings')
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='club_meetings', blank=True)
    
    class Meta:
        ordering = ['-scheduled_time']
    
    def __str__(self):
        return f"{self.club.name} - {self.title}"
    
    def can_start(self, user):
        """Check if user can start the meeting"""
        representatives = self.club.get_representatives()
        return user in representatives and self.status == 'scheduled'
    
    def start_meeting(self, user):
        """Start the meeting"""
        if self.can_start(user):
            from django.utils import timezone
            self.status = 'started'
            self.is_active = True
            self.started_at = timezone.now()
            self.started_by = user
            self.save()
            return True
        return False
    
    def end_meeting(self):
        """End the meeting"""
        if self.status == 'started':
            from django.utils import timezone
            self.status = 'ended'
            self.is_active = False
            self.ended_at = timezone.now()
            self.save()
            return True
        return False
    
    def is_upcoming(self):
        """Check if meeting is in the future"""
        from django.utils import timezone
        return self.scheduled_time > timezone.now() and self.status != 'ended'


class MeetingSignal(models.Model):
    """Stores WebRTC signaling messages for peer-to-peer connections"""
    meeting = models.ForeignKey(ClubMeeting, on_delete=models.CASCADE, related_name='signals')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_signals')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_signals', null=True, blank=True)
    signal_type = models.CharField(max_length=20)  # offer, answer, ice-candidate
    signal_data = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_consumed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.signal_type} from {self.sender.username} in meeting {self.meeting.id}"
