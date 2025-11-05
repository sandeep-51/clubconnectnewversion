from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from clubs.models import Club, Event, Membership, Message, Announcement
from accounts.models import User
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
from django.views.decorators.http import require_POST
from django.db.models import Count

def home(request):
    clubs = Club.objects.all()[:6]  # Get 6 clubs for display
    events = Event.objects.filter(start_time__gte=timezone.now()).order_by('start_time')[:4]  # Get 4 upcoming events
    announcements = Announcement.objects.all().order_by('-created_at')[:5]
    
    context = {
        'clubs': clubs,
        'events': events,
        'announcements': announcements,
    }
    return render(request, 'home.html', context)

@login_required
def events(request):
    return render(request, 'dashboard/events.html')

@login_required
def profile(request):
    user = request.user
    context = {
        'user': user,
    }
    return render(request, 'dashboard/profile.html', context)

@login_required
def dashboard(request):
    user = request.user
    clubs = Club.objects.all()[:5]  # Get 5 clubs for display
    events = Event.objects.filter(start_time__gte=timezone.now()).order_by('start_time')  # Get all upcoming events
    announcements = Announcement.objects.all().order_by('-created_at')[:3]  # Get 3 recent announcements
    user_clubs = []
    
    if user.is_student() or user.is_founder():
        memberships = Membership.objects.filter(user=user, status='approved')
        user_clubs = [membership.club for membership in memberships]
    
    # Get unread messages count
    unread_messages = Message.objects.filter(receiver=user, is_read=False).count()
    
    # Get all users for admin
    all_users = User.objects.all() if user.is_admin() else None

    # At-a-glance data
    next_event = events.first()
    recent_messages = Message.objects.filter(receiver=user).order_by('-created_at')[:3]
    
    # Gamification: Club of the Week
    club_of_the_week = Club.objects.order_by('?').first()

    context = {
        'clubs': clubs,
        'all_users': all_users,
        'announcements': announcements,
        'user_clubs': user_clubs,
        'unread_messages': unread_messages,
        'user_type': user.user_type,
        'next_event': next_event,
        'recent_messages': recent_messages,
        'upcoming_events': events[:4],
        'club_of_the_week': club_of_the_week,
    }
    
    # Render different templates based on user type
    if user.is_admin():
        from datetime import timedelta
        from django.db.models import Count
        from django.db.models.functions import TruncDate
        
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        
        total_users_count = User.objects.count()
        total_clubs_count = Club.objects.count()
        total_events_count = Event.objects.count()
        upcoming_events_count = Event.objects.filter(start_time__gte=now).count()
        
        context.update({
            'total_users': total_users_count,
            'total_clubs': total_clubs_count,
            'total_events': total_events_count,
            'upcoming_events_count': upcoming_events_count,
        })
        return render(request, 'dashboard/admin_dashboard.html', context)
    elif user.is_founder():
        from clubs.models import MentorSession, ClubFeedback, ClubMeeting
        founder_clubs = Club.objects.filter(founders=user)
        membership_requests = Membership.objects.filter(club__in=founder_clubs, status='pending')
        pending_mentor_sessions = MentorSession.objects.filter(club__in=founder_clubs, status='pending')
        pending_feedbacks = ClubFeedback.objects.filter(club__in=founder_clubs, status='pending')
        
        # Get upcoming meetings for founder clubs
        upcoming_meetings = ClubMeeting.objects.filter(
            club__in=founder_clubs,
            scheduled_time__gte=timezone.now()
        ).exclude(status='ended').order_by('scheduled_time')
        
        context.update({
            'membership_requests': membership_requests,
            'user_clubs': founder_clubs,  # Override with founder's clubs
            'pending_mentor_sessions': pending_mentor_sessions,
            'pending_feedbacks': pending_feedbacks,
            'upcoming_meetings': upcoming_meetings,
        })
        return render(request, 'dashboard/founder_dashboard.html', context)
    else:  # Default to student dashboard
        return render(request, 'dashboard/student_dashboard.html', context)

@login_required
def chat_view(request):
    user = request.user
    # Get all conversations for the current user
    conversations = Message.objects.filter(Q(sender=request.user) | Q(receiver=request.user)).order_by('-created_at')

    # Get a unique list of users the current user has had conversations with
    users_with_last_message = []
    users_in_conversations = []

    for message in conversations:
        other_user = None
        if message.sender != request.user and message.sender not in users_in_conversations:
            other_user = message.sender
            users_in_conversations.append(other_user)
        elif message.receiver != request.user and message.receiver not in users_in_conversations:
            other_user = message.receiver
            users_in_conversations.append(other_user)
        
        if other_user:
            last_message = Message.objects.filter(
                (Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user))
            ).latest('created_at')
            users_with_last_message.append({
                'user': other_user,
                'last_message': last_message
            })

    # Build recipient list based on role
    candidates = User.objects.exclude(id=user.id)
    allowed_recipients = []

    if user.is_admin():
        allowed_recipients = candidates.order_by('username')
    elif user.is_founder():
        # Founders can message approved club members and admins
        founder_clubs = Club.objects.filter(founders=user)
        member_ids = Membership.objects.filter(club__in=founder_clubs, status='approved').values_list('user_id', flat=True)
        club_members = User.objects.filter(id__in=member_ids)
        admins = candidates.filter(user_type='admin')
        allowed_recipients = (club_members | admins).distinct().order_by('username')
    else:  # student
        # Students can message any founder and admins (not limited to joined clubs)
        founders = candidates.filter(user_type='founder')
        admins = candidates.filter(user_type='admin')
        allowed_recipients = (founders | admins).distinct().order_by('username')

    # Add users from allowed_recipients who are not in conversations yet
    for recipient in allowed_recipients:
        if recipient not in users_in_conversations:
            users_with_last_message.append({
                'user': recipient,
                'last_message': None
            })

    context = {
        'users_with_last_message': users_with_last_message,
    }
    return render(request, 'dashboard/chat.html', context)




@login_required
def my_week(request):
    return render(request, 'dashboard/my_week.html')

@login_required
def search(request):
    query = request.GET.get('q')
    results = {}
    if query:
        # Search users, clubs, events, and announcements
        user_results = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
        club_results = Club.objects.filter(name__icontains=query)
        event_results = Event.objects.filter(title__icontains=query)
        announcement_results = Announcement.objects.filter(title__icontains=query)

        if user_results:
            results['users'] = list(user_results)
        if club_results:
            results['clubs'] = list(club_results)
        if event_results:
            results['events'] = list(event_results)
        if announcement_results:
            results['announcements'] = list(announcement_results)

    context = {
        'query': query,
        'results': results,
    }
    return render(request, 'dashboard/search_results.html', context)

@login_required
def notifications(request):
    from clubs.models import Notification
    all_notifications = Notification.objects.filter(user=request.user)
    unread_count = all_notifications.filter(is_read=False).count()
    user_notifications = all_notifications.order_by('-created_at')[:20]
    
    context = {
        'notifications': user_notifications,
        'unread_count': unread_count,
    }
    return render(request, 'dashboard/notifications.html', context)

@login_required
def my_clubs(request):
    user = request.user
    if user.is_founder():
        clubs = Club.objects.filter(founders=user)
    else:
        memberships = Membership.objects.filter(user=user, status='approved')
        clubs = [membership.club for membership in memberships]
    
    context = {
        'clubs': clubs,
    }
    return render(request, 'dashboard/my_clubs.html', context)

@login_required
def manage_users(request):
    # Ensure user is admin
    if not request.user.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    users = User.objects.all()
    return render(request, 'dashboard/manage_users.html', {'users': users})

@login_required
def manage_clubs(request):
    # Ensure user is admin
    if not request.user.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    clubs = Club.objects.all()
    return render(request, 'dashboard/manage_clubs.html', {'clubs': clubs})

from sitetheme.models import ThemeSettings

@login_required
def manage_settings(request):
    # Ensure user is admin
    if not request.user.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    theme_settings, created = ThemeSettings.objects.get_or_create(pk=1)

    if request.method == 'POST':
        if 'primary_color' in request.POST:
            primary_color = request.POST.get('primary_color')
            secondary_color = request.POST.get('secondary_color')
            theme_settings.primary_color = primary_color
            theme_settings.secondary_color = secondary_color
            theme_settings.save()
            messages.success(request, "Theme settings updated successfully.")
        elif 'announcement_duration' in request.POST:
            # Save announcement settings
            messages.success(request, "Announcement settings updated successfully.")
        elif 'max_clubs_per_student' in request.POST:
            # Save club registration settings
            messages.success(request, "Club registration settings updated successfully.")
    
    return render(request, 'dashboard/manage_settings.html', {'theme_settings': theme_settings})

@login_required
def edit_user(request, user_id):
    # Ensure user is admin
    if not request.user.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    user_to_edit = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Process form data
        user_type = request.POST.get('user_type')
        is_active = 'is_active' in request.POST
        
        user_to_edit.user_type = user_type
        user_to_edit.is_active = is_active
        user_to_edit.save()
        
        messages.success(request, f"User {user_to_edit.username} updated successfully.")
        return redirect('manage_users')
    
    return render(request, 'dashboard/edit_user.html', {'user_to_edit': user_to_edit})

@login_required
def delete_user(request, user_id):
    # Ensure user is admin
    if not request.user.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    user_to_delete = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"User {username} has been deleted.")
        return redirect('manage_users')
    
    return render(request, 'dashboard/delete_user_confirm.html', {'user_to_delete': user_to_delete})



@login_required
def create_announcement(request):
    if not request.user.is_staff:
        return redirect('dashboard')

    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')

        if title and content:
            announcement = Announcement.objects.create(
                title=title,
                content=content,
                author=request.user,
                club=None
            )
            
            from clubs.models import Notification
            from clubs.utils import create_notification
            
            all_users = User.objects.all()
            create_notification(
                all_users,
                'announcement',
                f'New Announcement: {title}',
                content,
                '/dashboard/'
            )
            
            messages.success(request, 'Announcement created and notifications sent successfully.')
            return redirect('dashboard')

    return render(request, 'dashboard/create_announcement.html')

@login_required
def reset_user_password(request, user_id):
    # Ensure user is admin
    if not request.user.is_admin():
        messages.error(request, "You don't have permission to access this page.")
        return redirect('dashboard')
    
    user_to_reset = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password == confirm_password:
                if len(new_password) >= 8:
                    user_to_reset.set_password(new_password)
                    user_to_reset.save()
                    messages.success(request, f"Password for {user_to_reset.username} has been reset successfully.")
                    return redirect('manage_users')
                else:
                    messages.error(request, "Password must be at least 8 characters long.")
            else:
                messages.error(request, "Passwords do not match.")
        else:
            messages.error(request, "Please fill in both password fields.")
    
    return render(request, 'dashboard/reset_password.html', {'user_to_reset': user_to_reset})


@login_required
@require_POST
def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    if announcement.club:
        if not announcement.club.founders.filter(id=request.user.id).exists() and not request.user.is_admin():
            messages.error(request, "You are not authorized to delete this announcement.")
            return redirect('club_detail', club_id=announcement.club.id)
        redirect_url = 'club_detail'
        redirect_id = announcement.club.id
    else:
        if not request.user.is_admin():
            messages.error(request, "You are not authorized to delete this announcement.")
            return redirect('dashboard')
        redirect_url = 'dashboard'
        redirect_id = None
    
    announcement.delete()
    messages.success(request, "Announcement deleted successfully.")
    
    if redirect_id:
        return redirect(redirect_url, club_id=redirect_id)
    return redirect(redirect_url)




@login_required
def get_messages(request, user_id):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'User not authenticated'}, status=401)

    other_user = get_object_or_404(User, id=user_id)
    
    # Mark messages as read
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

    messages = Message.objects.filter(
        (Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user))
    ).order_by('created_at')

    message_list = []
    for message in messages:
        message_list.append({
            'id': message.id,
            'sender': message.sender.username,
            'receiver': message.receiver.username,
            'content': message.content,
            'created_at': message.created_at.isoformat()
        })

    return JsonResponse({'messages': message_list})

@require_POST
@login_required
def edit_message(request, message_id):
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    data = json.loads(request.body)
    new_content = data.get('content')

    if new_content:
        message.content = new_content
        message.save()
        return JsonResponse({'status': 'Message edited'})
    return JsonResponse({'error': 'No content provided'}, status=400)

@require_POST
@login_required
def unsend_message(request, message_id):
    message = get_object_or_404(Message, id=message_id, sender=request.user)
    message.content = "This message was unsent."
    message.save()
    return JsonResponse({'status': 'Message unsent'})

@require_POST
@login_required
def mark_messages_as_read(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok'})

@login_required
def unread_messages_count(request):
    unread_count = Message.objects.filter(receiver=request.user, is_read=False).count()
    unread_senders = Message.objects.filter(receiver=request.user, is_read=False)\
        .values('sender')\
        .annotate(count=Count('sender'))
    
    unread_senders_dict = {item['sender']: item['count'] for item in unread_senders}

    return JsonResponse({'unread_count': unread_count, 'unread_senders': unread_senders_dict})


@csrf_exempt
def send_message(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'User not authenticated'}, status=401)

        data = json.loads(request.body)
        receiver_id = data.get('receiver_id')
        content = data.get('content')

        if not receiver_id or not content:
            return JsonResponse({'error': 'Missing receiver_id or content'}, status=400)

        receiver = get_object_or_404(User, id=receiver_id)
        message = Message.objects.create(
            sender=request.user,
            receiver=receiver,
            content=content
        )

        return JsonResponse({'status': 'Message sent'})

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def mark_notification_read(request, notification_id):
    from clubs.models import Notification
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return JsonResponse({'status': 'success'})


@login_required
def get_unread_notifications_count(request):
    from clubs.models import Notification
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': unread_count})


@login_required
def admin_analytics_data(request):
    if not request.user.is_admin():
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    from datetime import datetime, timedelta
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    
    from django.db.models import Q
    
    signin_labels = []
    signin_data = []
    signup_data = []
    
    daily_signins_dict = {}
    for user in User.objects.filter(last_seen__gte=seven_days_ago, last_seen__isnull=False):
        date_key = user.last_seen.date()
        daily_signins_dict[date_key] = daily_signins_dict.get(date_key, 0) + 1
    
    daily_signups_dict = {}
    for user in User.objects.filter(date_joined__gte=seven_days_ago):
        date_key = user.date_joined.date()
        daily_signups_dict[date_key] = daily_signups_dict.get(date_key, 0) + 1
    
    today = now.date()
    start_date = (now - timedelta(days=6)).date()
    
    for i in range(7):
        date = start_date + timedelta(days=i)
        signin_labels.append(date.strftime('%b %d'))
        signin_data.append(daily_signins_dict.get(date, 0))
        signup_data.append(daily_signups_dict.get(date, 0))
    
    total_users = User.objects.count()
    total_clubs = Club.objects.count()
    total_events = Event.objects.count()
    upcoming_events = Event.objects.filter(start_time__gte=now).count()
    
    total_announcements = Announcement.objects.count()
    
    return JsonResponse({
        'signin_labels': signin_labels,
        'signin_data': signin_data,
        'signup_data': signup_data,
        'total_users': total_users,
        'total_clubs': total_clubs,
        'total_events': total_events,
        'upcoming_events': upcoming_events,
        'total_announcements': total_announcements,
    })


@login_required
def activity_feed(request):
    from clubs.models import ClubPost
    from datetime import timedelta
    
    now = timezone.now()
    recent_announcements = Announcement.objects.all().order_by('-created_at')[:10]
    upcoming_events = Event.objects.filter(start_time__gte=now).order_by('start_time')[:10]
    recent_posts = ClubPost.objects.all().order_by('-created_at')[:10]
    
    activity_items = []
    
    for announcement in recent_announcements:
        activity_items.append({
            'type': 'announcement',
            'title': announcement.title,
            'content': announcement.content,
            'club': announcement.club.name if announcement.club else 'General',
            'created_at': announcement.created_at,
            'link': f'/clubs/{announcement.club.id}/' if announcement.club else '#',
        })
    
    for event in upcoming_events:
        activity_items.append({
            'type': 'event',
            'title': event.title,
            'content': event.description,
            'club': event.club.name,
            'created_at': event.start_time,
            'link': f'/clubs/{event.club.id}/',
        })
    
    for post in recent_posts:
        activity_items.append({
            'type': 'post',
            'title': post.title,
            'content': post.content,
            'club': post.club.name,
            'created_at': post.created_at,
            'link': f'/clubs/{post.club.id}/',
        })
    
    activity_items.sort(key=lambda x: x['created_at'], reverse=True)
    activity_items = activity_items[:20]
    
    return render(request, 'dashboard/activity_feed.html', {'activity_items': activity_items})


@login_required
def student_club_meetings(request):
    """View for students to see all club meetings from clubs they're members of"""
    from clubs.models import ClubMeeting
    
    # Get all clubs where user is an approved member
    user_memberships = Membership.objects.filter(user=request.user, status='approved')
    user_clubs = [membership.club for membership in user_memberships]
    
    # Get all upcoming meetings from these clubs
    upcoming_meetings = ClubMeeting.objects.filter(
        club__in=user_clubs,
        scheduled_time__gte=timezone.now()
    ).exclude(status='ended').order_by('scheduled_time')
    
    context = {
        'meetings': upcoming_meetings,
        'user_clubs': user_clubs,
    }
    
    return render(request, 'dashboard/student_club_meetings.html', context)
