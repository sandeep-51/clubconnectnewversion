from django.contrib.auth.signals import user_logged_in
from django.contrib.sessions.models import Session
from django.dispatch import receiver
from .models import User


@receiver(user_logged_in)
def invalidate_other_sessions(sender, request, user, **kwargs):
    """
    When a user logs in, invalidate all other sessions for that user.
    This enforces single-device login.
    """
    # Get the current session key
    current_session_key = request.session.session_key
    
    # If user has a previous session key and it's different from current
    if user.current_session_key and user.current_session_key != current_session_key:
        try:
            # Delete the old session
            old_session = Session.objects.get(session_key=user.current_session_key)
            old_session.delete()
        except Session.DoesNotExist:
            pass
    
    # Update user's current session key
    user.current_session_key = current_session_key
    user.save(update_fields=['current_session_key'])
