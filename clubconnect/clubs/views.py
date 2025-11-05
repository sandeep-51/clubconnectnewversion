from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from .models import Club, Event, Membership, Message, Announcement
from accounts.models import User
from .forms import ClubForm, EventForm, ClubRegistrationForm, MessageForm, AnnouncementForm

@login_required
def clubs_list(request):
    clubs = Club.objects.all()
    return render(request, 'clubs/clubs_list.html', {'clubs': clubs})

# Admin-only club creation
@login_required
def create_club(request):
    if not request.user.is_admin():
        messages.error(request, "Only administrators can create clubs.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ClubForm(request.POST, request.FILES)
        if form.is_valid():
            club = form.save()
            messages.success(request, f"Club '{club.name}' has been created successfully.")
            return redirect('assign_founder', club_id=club.id)
    else:
        form = ClubForm()
    
    return render(request, 'clubs/create_club.html', {'form': form})

# Admin assigns founder to club
@login_required
def assign_founder(request, club_id):
    if not request.user.is_admin():
        messages.error(request, "Only administrators can assign founders.")
        return redirect('dashboard')
    
    club = get_object_or_404(Club, id=club_id)
    query = request.GET.get('q', '').strip()
    # Default list shows existing founders; when searching, include students matching query
    base_qs = User.objects.filter(user_type='founder')
    if query:
        search_qs = User.objects.filter(user_type__in=['founder', 'student']).filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
        potential_founders = search_qs.order_by('username')
    else:
        potential_founders = base_qs.order_by('username')
    
    if request.method == 'POST':
        founder_id = request.POST.get('founder_id')
        if founder_id:
            user_obj = get_object_or_404(User, id=founder_id)
            # Promote student to founder if needed
            if user_obj.user_type == 'student':
                user_obj.user_type = 'founder'
                user_obj.save()
                messages.info(request, f"{user_obj.username} was promoted to Founder.")
            # Assign as founder for the club
            club.founders.add(user_obj)
            messages.success(request, f"{user_obj.username} has been assigned as a founder of {club.name}.")
            return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/assign_founder.html', {
        'club': club,
        'potential_founders': potential_founders,
        'query': query,
    })

# Club detail view
def club_detail(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    events = Event.objects.filter(club=club).order_by('start_time').prefetch_related('attendances__user')
    founders = club.founders.all()
    announcements = Announcement.objects.filter(club=club).order_by('-created_at')[:5]
    is_member = False
    
    if request.user.is_authenticated:
        is_member = Membership.objects.filter(user=request.user, club=club, status='approved').exists()
    
    from .models import ClubPost, Survey
    recent_posts = ClubPost.objects.filter(club=club).order_by('-created_at')[:5]
    active_surveys = Survey.objects.filter(club=club, is_active=True)
    
    user_registered_events = []
    if request.user.is_authenticated:
        from .models import EventAttendance
        user_registered_events = EventAttendance.objects.filter(
            event__club=club, 
            user=request.user
        ).values_list('event_id', flat=True)
    
    context = {
        'club': club,
        'events': events,
        'founders': founders,
        'announcements': announcements,
        'is_member': is_member,
        'recent_posts': recent_posts,
        'active_surveys': active_surveys,
        'user_registered_events': user_registered_events,
    }
    return render(request, 'clubs/club_detail.html', context)

# Search clubs
def search_clubs(request):
    query = request.GET.get('q', '')
    clubs = Club.objects.all()
    
    if query:
        clubs = clubs.filter(
            Q(name__icontains=query) | 
            Q(short_description__icontains=query) |
            Q(domain_tags__icontains=query)
        )
    
    context = {
        'clubs': clubs,
        'query': query,
    }
    return render(request, 'clubs/search_results.html', context)

# Club registration for students
@login_required
def register_for_club(request, club_id):
    if not request.user.is_student():
        messages.error(request, "Only students can register for clubs.")
        return redirect('club_detail', club_id=club_id)
    
    club = get_object_or_404(Club, id=club_id)
    
    # Check if already a member or has pending request
    existing_membership = Membership.objects.filter(user=request.user, club=club).first()
    if existing_membership:
        if existing_membership.status == 'approved':
            messages.info(request, "You are already a member of this club.")
        elif existing_membership.status == 'pending':
            messages.info(request, "Your membership request is pending approval.")
        else:
            messages.info(request, "Your previous membership request was rejected.")
        return redirect('club_detail', club_id=club_id)
    
    if request.method == 'POST':
        form = ClubRegistrationForm(request.POST)
        if form.is_valid():
            membership = Membership(
                user=request.user,
                club=club,
                status='pending'
            )
            membership.save()
            messages.success(request, f"Your registration request for {club.name} has been submitted.")
            return redirect('dashboard')
    else:
        form = ClubRegistrationForm()
    
    return render(request, 'clubs/register_for_club.html', {'form': form, 'club': club})

# Direct messaging between students and founders
@login_required
def send_message_to_founder(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    founders = club.founders.all()
    
    if request.method == 'POST':
        founder_id = request.POST.get('founder_id')
        content = request.POST.get('content')
        
        if founder_id and content:
            founder = get_object_or_404(User, id=founder_id)
            message = Message(
                sender=request.user,
                receiver=founder,
                content=content,
                is_read=False
            )
            message.save()
            messages.success(request, "Your message has been sent to the club founder.")
            return redirect('club_detail', club_id=club_id)
    
    return render(request, 'clubs/send_message.html', {'club': club, 'founders': founders})

@login_required
def edit_club(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    # Check if user is a founder of this club
    if not club.founders.filter(id=request.user.id).exists():
        messages.error(request, "Only club founders can edit club information.")
        return redirect('club_detail', club_id=club_id)
    
    if request.method == 'POST':
        form = ClubForm(request.POST, request.FILES, instance=club)
        if form.is_valid():
            form.save()
            messages.success(request, f"Club '{club.name}' has been updated successfully.")
            return redirect('club_detail', club_id=club_id)
    else:
        form = ClubForm(instance=club)
    
    return render(request, 'clubs/edit_club.html', {'form': form, 'club': club})
@login_required
def create_event(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    if not club.founders.filter(id=request.user.id).exists():
        messages.error(request, "Only club founders can create events.")
        return redirect('club_detail', club_id=club_id)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.club = club
            event.save()
            
            from .models import Notification
            from .utils import create_notification
            favorited_users = list(club.favorited_by.all())
            if favorited_users:
                create_notification(
                    favorited_users,
                    'event',
                    f'New Event in {club.name}!',
                    f'{event.title} - {event.description[:100]}...',
                    f'/clubs/{club.id}/'
                )
            
            notify_club_members(
                club,
                'event',
                f'New Event: {event.title}',
                event.description[:100],
                f'/clubs/{club.id}/'
            )
            
            messages.success(request, f"Event '{event.title}' has been created and members notified!")
            return redirect('club_detail', club_id=club_id)
    else:
        form = EventForm()
    return render(request, 'clubs/create_event.html', {'form': form, 'club': club})

# Club member chat for members
@login_required
def club_chat(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    # Check if user is a founder or member of this club
    is_founder = club.founders.filter(id=request.user.id).exists()
    is_member = Membership.objects.filter(user=request.user, club=club, status='approved').exists()
    
    if not (is_founder or is_member):
        messages.error(request, "You must be a founder or member to access the club chat.")
        return redirect('club_detail', club_id=club.id)
    
    # Get all approved members
    members = Membership.objects.filter(club=club, status='approved')

    # Build recipient list: founders (for students) or members/admins (for founders)
    if is_founder:
        recipient_users = User.objects.filter(id__in=members.values_list('user_id', flat=True)) | User.objects.filter(user_type='admin')
    else:
        recipient_users = club.founders.all()
    recipient_users = recipient_users.distinct().order_by('username')

    # Handle sending a message
    if request.method == 'POST':
        receiver_id = request.POST.get('receiver_id')
        content = request.POST.get('content')
        if receiver_id and content:
            receiver = get_object_or_404(User, id=receiver_id)
            Message.objects.create(
                sender=request.user,
                receiver=receiver,
                club=club,
                content=content.strip(),
                is_read=False,
            )
            messages.success(request, 'Message sent.')
            return redirect('club_chat', club_id=club_id)
        messages.error(request, 'Please select a recipient and enter a message.')

    # Load club-specific messages (between founders and members only)
    messages_qs = Message.objects.filter(club=club).order_by('created_at')
    
    context = {
        'club': club,
        'members': members,
        'is_founder': is_founder,
        'recipient_users': recipient_users,
        'messages': messages_qs,
    }
    return render(request, 'clubs/club_chat.html', context)

@login_required
def approve_membership(request, membership_id):
    membership = get_object_or_404(Membership, id=membership_id)
    club = membership.club

    # Ensure the user is a founder of the club
    if not club.founders.filter(id=request.user.id).exists():
        messages.error(request, "Only club founders can approve memberships.")
        return redirect('club_detail', club_id=club.id)

    membership.status = 'approved'
    membership.save()
    messages.success(request, f"Membership for {membership.user.username} has been approved.")
    return redirect('founder_dashboard')

@login_required
def leave_club(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    membership = get_object_or_404(Membership, user=request.user, club=club)

    if request.method == 'POST':
        membership.delete()
        messages.success(request, f"You have left {club.name}.")
        return redirect('club_detail', club_id=club.id)

    return render(request, 'clubs/leave_club_confirm.html', {'club': club})

@login_required
def reject_membership(request, membership_id):
    membership = get_object_or_404(Membership, id=membership_id)
    club = membership.club

    # Ensure the user is a founder of the club
    if not club.founders.filter(id=request.user.id).exists():
        messages.error(request, "Only club founders can reject memberships.")
        return redirect('club_detail', club_id=club.id)

    membership.status = 'rejected'
    membership.save()
    messages.success(request, f"Membership for {membership.user.username} has been rejected.")
    return redirect('founder_dashboard')

@login_required
def create_club_announcement(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    if not club.founders.filter(id=request.user.id).exists() and not request.user.is_staff:
        messages.error(request, "You are not authorized to create an announcement for this club.")
        return redirect('club_detail', club_id=club.id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.club = club
            announcement.author = request.user
            announcement.save()
            
            from .utils import notify_club_members
            notify_club_members(
                club,
                'announcement',
                f'New Announcement in {club.name}',
                announcement.title,
                f'/clubs/{club.id}/'
            )
            
            messages.success(request, "Announcement created and members notified successfully.")
            return redirect('club_detail', club_id=club.id)
    else:
        form = AnnouncementForm()

    return render(request, 'clubs/create_club_announcement.html', {'form': form, 'club': club})

@login_required
def delete_club_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    club = announcement.club
    if not club.founders.filter(id=request.user.id).exists() and not request.user.is_staff:
        messages.error(request, "You are not authorized to delete this announcement.")
        return redirect('club_detail', club_id=club.id)

    announcement.delete()
    messages.success(request, "Announcement deleted successfully.")
    return redirect('club_detail', club_id=club.id)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Event, EventAttendance, Survey, SurveyQuestion, SurveyResponse, ClubPost, MemberPoints, Club, Membership
from .utils import generate_qr_code_for_event, notify_club_members
from accounts.models import User


@login_required
def generate_event_qr(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    club = event.club
    
    if not club.founders.filter(id=request.user.id).exists() and not request.user.is_admin():
        messages.error(request, "Only club founders can generate QR codes.")
        return redirect('club_detail', club_id=club.id)
    
    if not event.qr_code:
        generate_qr_code_for_event(event, request)
        messages.success(request, "QR code generated successfully!")
    
    return redirect('club_detail', club_id=club.id)


@login_required
def event_checkin(request, event_id):
    """Student-side or founder-initiated check-in"""
    event = get_object_or_404(Event, id=event_id)
    user_id = request.GET.get('user_id')
    
    # If user_id is provided and requester is authorized, check in that user
    is_authorized = (
        event.club.founders.filter(id=request.user.id).exists() or
        request.user == event.club.president or
        request.user == event.club.vice_president or
        request.user.is_admin()
    )
    
    if user_id and is_authorized:
        user_to_checkin = get_object_or_404(User, id=user_id)
        attendance = EventAttendance.objects.filter(event=event, user=user_to_checkin).first()
        
        if attendance and not attendance.checked_in_via_qr:
            attendance.checked_in_via_qr = True
            attendance.save()
            
            member_points, _ = MemberPoints.objects.get_or_create(
                user=user_to_checkin,
                club=event.club
            )
            member_points.participation_count += 1
            member_points.points += 10
            member_points.save()
            
            messages.success(request, f"Successfully checked in {user_to_checkin.username} to {event.title}!")
        elif attendance and attendance.checked_in_via_qr:
            messages.info(request, f"{user_to_checkin.username} is already checked in.")
        else:
            messages.error(request, f"{user_to_checkin.username} is not registered for this event.")
        
        return redirect('manage_event_attendance', event_id=event.id)
    
    # Regular student check-in
    attendance, created = EventAttendance.objects.get_or_create(
        event=event,
        user=request.user,
        defaults={'checked_in_via_qr': True}
    )
    
    if not created and not attendance.checked_in_via_qr:
        attendance.checked_in_via_qr = True
        attendance.save()
        created = True
    
    if created or not attendance.checked_in_via_qr:
        member_points, _ = MemberPoints.objects.get_or_create(
            user=request.user,
            club=event.club
        )
        member_points.participation_count += 1
        member_points.points += 10
        member_points.save()
        
        messages.success(request, f"Successfully checked in to {event.title}! You earned 10 points.")
    else:
        messages.info(request, "You have already checked in to this event.")
    
    return redirect('club_detail', club_id=event.club.id)

@login_required
def event_register(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    attendance, created = EventAttendance.objects.get_or_create(
        event=event,
        user=request.user,
        defaults={'checked_in_via_qr': False}
    )
    
    if created:
        from .models import Notification
        from .utils import create_notification
        representatives = event.club.get_representatives()
        create_notification(
            representatives,
            'event',
            f'New Registration for {event.title}',
            f'{request.user.username} registered for the event',
            f'/clubs/{event.club.id}/'
        )
        messages.success(request, f"Successfully registered for {event.title}! Don't forget to check in at the event to earn points.")
    else:
        messages.info(request, "You are already registered for this event.")
    
    return redirect('club_detail', club_id=event.club.id)


@login_required
def download_event_qr(request, event_id):
    """Generate and download QR code for student's event registration"""
    from .models import EventAttendance
    
    event = get_object_or_404(Event, id=event_id)
    
    attendance = EventAttendance.objects.filter(event=event, user=request.user).first()
    if not attendance:
        messages.error(request, "You are not registered for this event.")
        return redirect('club_detail', club_id=event.club.id)
    
    import qrcode
    from io import BytesIO
    from django.http import HttpResponse
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    checkin_url = request.build_absolute_uri(
        f'/clubs/event/{event.id}/checkin/?user_id={request.user.id}'
    )
    
    qr.add_data(checkin_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="event_qr_{event.id}_{request.user.username}.png"'
    
    return response


@login_required
def create_survey(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    if not club.founders.filter(id=request.user.id).exists():
        messages.error(request, "Only club founders can create surveys.")
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        
        if title:
            survey = Survey.objects.create(
                club=club,
                creator=request.user,
                title=title,
                description=description
            )
            
            question_count = int(request.POST.get('question_count', 0))
            for i in range(question_count):
                question_text = request.POST.get(f'question_{i}')
                question_type = request.POST.get(f'type_{i}', 'text')
                choices = request.POST.get(f'choices_{i}', '')
                
                if question_text:
                    SurveyQuestion.objects.create(
                        survey=survey,
                        question_text=question_text,
                        question_type=question_type,
                        choices=choices,
                        order=i
                    )
            
            notify_club_members(
                club,
                'general',
                'New Survey Available',
                f'A new survey "{title}" has been created in {club.name}',
                f'/clubs/{club.id}/surveys/{survey.id}/'
            )
            
            messages.success(request, "Survey created successfully!")
            return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/create_survey.html', {'club': club})


@login_required
def view_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    questions = survey.questions.all()
    
    user_responses = SurveyResponse.objects.filter(survey=survey, user=request.user)
    has_responded = user_responses.exists()
    
    if request.method == 'POST' and not has_responded:
        for question in questions:
            answer = request.POST.get(f'question_{question.id}')
            if answer:
                SurveyResponse.objects.create(
                    survey=survey,
                    user=request.user,
                    question=question,
                    answer=answer
                )
        
        member_points, _ = MemberPoints.objects.get_or_create(
            user=request.user,
            club=survey.club
        )
        member_points.contribution_count += 1
        member_points.points += 5
        member_points.save()
        
        messages.success(request, "Thank you for completing the survey! You earned 5 points.")
        return redirect('club_detail', club_id=survey.club.id)
    
    context = {
        'survey': survey,
        'questions': questions,
        'has_responded': has_responded,
    }
    return render(request, 'clubs/view_survey.html', context)


@login_required
def survey_results(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    
    if not survey.club.founders.filter(id=request.user.id).exists() and not request.user.is_admin():
        messages.error(request, "Only club founders can view survey results.")
        return redirect('club_detail', club_id=survey.club.id)
    
    questions = survey.questions.all()
    results = []
    
    for question in questions:
        question_responses = SurveyResponse.objects.filter(question=question)
        
        if question.question_type == 'choice':
            choices = [c.strip() for c in question.choices.split(',')]
            choice_counts = {choice: 0 for choice in choices}
            
            for response in question_responses:
                if response.answer in choice_counts:
                    choice_counts[response.answer] += 1
            
            results.append({
                'question': question.question_text,
                'type': 'choice',
                'data': choice_counts,
            })
        elif question.question_type == 'rating':
            ratings = [int(r.answer) for r in question_responses if r.answer.isdigit()]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            rating_counts = {i: ratings.count(i) for i in range(1, 6)}
            
            results.append({
                'question': question.question_text,
                'type': 'rating',
                'average': round(avg_rating, 2),
                'data': rating_counts,
            })
        else:
            text_responses = [r.answer for r in question_responses]
            results.append({
                'question': question.question_text,
                'type': 'text',
                'responses': text_responses,
            })
    
    context = {
        'survey': survey,
        'results': results,
        'total_responses': SurveyResponse.objects.filter(survey=survey).values('user').distinct().count(),
    }
    return render(request, 'clubs/survey_results.html', context)


@login_required
def create_club_post(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    is_founder = club.founders.filter(id=request.user.id).exists()
    is_president = request.user == club.president
    is_vp = request.user == club.vice_president
    
    if not (is_founder or is_president or is_vp):
        messages.error(request, "Only club representatives can create posts.")
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        post_type = request.POST.get('post_type', 'general')
        image = request.FILES.get('image')
        
        if title and content:
            post = ClubPost.objects.create(
                club=club,
                author=request.user,
                post_type=post_type,
                title=title,
                content=content,
                image=image
            )
            
            notify_club_members(
                club,
                'general',
                f'New {post_type} from {request.user.username}',
                title,
                f'/clubs/{club.id}/'
            )
            
            member_points, _ = MemberPoints.objects.get_or_create(
                user=request.user,
                club=club
            )
            member_points.contribution_count += 1
            member_points.points += 3
            member_points.save()
            
            messages.success(request, "Post created successfully!")
            return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/create_post.html', {'club': club})


@login_required
def like_post(request, post_id):
    post = get_object_or_404(ClubPost, id=post_id)
    
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        liked = False
    else:
        post.likes.add(request.user)
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'total_likes': post.total_likes()
    })


@login_required
def club_leaderboard(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    leaderboard = MemberPoints.objects.filter(club=club).select_related('user')[:20]
    
    context = {
        'club': club,
        'leaderboard': leaderboard,
    }
    return render(request, 'clubs/leaderboard.html', context)


@login_required
def toggle_favorite_club(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    if request.user in club.favorited_by.all():
        club.favorited_by.remove(request.user)
        favorited = False
        messages.success(request, f"Removed {club.name} from your favorites.")
    else:
        club.favorited_by.add(request.user)
        favorited = True
        messages.success(request, f"Added {club.name} to your favorites!")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'favorited': favorited})
    return redirect('club_detail', club_id=club.id)


@login_required
def submit_club_feedback(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        feedback_type = request.POST.get('feedback_type', 'feedback')
        
        if title and description:
            from .models import ClubFeedback
            feedback = ClubFeedback.objects.create(
                club=club,
                student=request.user,
                feedback_type=feedback_type,
                title=title,
                description=description
            )
            
            from .models import Notification
            from .utils import create_notification
            representatives = club.get_representatives()
            create_notification(
                representatives,
                'general',
                f'New {feedback.get_feedback_type_display()} from {request.user.username}',
                f'{title}: {description[:100]}...',
                f'/clubs/{club.id}/feedback/'
            )
            
            messages.success(request, "Your feedback has been submitted successfully!")
            return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/submit_feedback.html', {'club': club})


@login_required
def view_club_feedbacks(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    if not club.founders.filter(id=request.user.id).exists() and request.user != club.president and request.user != club.vice_president:
        messages.error(request, "Only club representatives can view feedbacks.")
        return redirect('club_detail', club_id=club.id)
    
    from .models import ClubFeedback
    feedbacks = ClubFeedback.objects.filter(club=club)
    
    return render(request, 'clubs/view_feedbacks.html', {'club': club, 'feedbacks': feedbacks})


@login_required
def update_feedback_status(request, feedback_id):
    from .models import ClubFeedback
    feedback = get_object_or_404(ClubFeedback, id=feedback_id)
    club = feedback.club
    
    if not club.founders.filter(id=request.user.id).exists() and request.user != club.president and request.user != club.vice_president:
        messages.error(request, "Only club representatives can update feedback status.")
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['pending', 'reviewed', 'implemented']:
            feedback.status = status
            feedback.reviewed_by = request.user
            feedback.save()
            
            from .models import Notification
            from .utils import create_notification
            create_notification(
                [feedback.student],
                'general',
                f'Feedback Status Updated: {feedback.title}',
                f'Your feedback has been marked as {status}',
                f'/clubs/{club.id}/'
            )
            
            messages.success(request, "Feedback status updated successfully!")
    
    return redirect('view_club_feedbacks', club_id=club.id)


@login_required
def book_mentor_session(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    is_member = Membership.objects.filter(user=request.user, club=club, status='approved').exists()
    if not is_member:
        messages.error(request, "You must be a club member to book a mentor session.")
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        mentor_topic = request.POST.get('mentor_topic')
        description = request.POST.get('description')
        preferred_date = request.POST.get('preferred_date')
        
        if mentor_topic and description and preferred_date:
            from .models import MentorSession
            from datetime import datetime
            from django.utils import timezone as tz
            
            naive_datetime = datetime.fromisoformat(preferred_date)
            aware_datetime = tz.make_aware(naive_datetime)
            
            session = MentorSession.objects.create(
                club=club,
                student=request.user,
                mentor_topic=mentor_topic,
                description=description,
                preferred_date=aware_datetime
            )
            
            from .models import Notification
            from .utils import create_notification
            representatives = club.get_representatives()
            create_notification(
                representatives,
                'general',
                f'New Mentor Session Request from {request.user.username}',
                f'Topic: {mentor_topic}',
                f'/clubs/{club.id}/mentor-sessions/'
            )
            
            messages.success(request, "Mentor session request submitted successfully! Club representatives will review it soon.")
            return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/book_mentor_session.html', {'club': club})


@login_required
def view_mentor_sessions(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    if not club.founders.filter(id=request.user.id).exists() and request.user != club.president and request.user != club.vice_president:
        messages.error(request, "Only club representatives can view mentor sessions.")
        return redirect('club_detail', club_id=club.id)
    
    from .models import MentorSession
    sessions = MentorSession.objects.filter(club=club)
    
    return render(request, 'clubs/view_mentor_sessions.html', {'club': club, 'sessions': sessions})


@login_required
def update_mentor_session(request, session_id):
    from .models import MentorSession
    session = get_object_or_404(MentorSession, id=session_id)
    club = session.club
    
    if not club.founders.filter(id=request.user.id).exists() and request.user != club.president and request.user != club.vice_president:
        messages.error(request, "Only club representatives can manage mentor sessions.")
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        meeting_link = request.POST.get('meeting_link', '')
        
        if status in ['approved', 'rejected', 'completed']:
            session.status = status
            session.assigned_mentor = request.user
            session.meeting_link = meeting_link
            session.save()
            
            from .models import Notification
            from .utils import create_notification
            create_notification(
                [session.student],
                'general',
                f'Mentor Session {status.title()}: {session.mentor_topic}',
                f'Your mentor session has been {status}. {"Meeting link: " + meeting_link if meeting_link else ""}',
                f'/clubs/{club.id}/'
            )
            
            messages.success(request, f"Mentor session {status} successfully!")
    
    return redirect('view_mentor_sessions', club_id=club.id)


@login_required
def create_club_meeting(request, club_id):
    club = get_object_or_404(Club, id=club_id)
    
    if not club.founders.filter(id=request.user.id).exists() and request.user != club.president and request.user != club.vice_president:
        messages.error(request, "Only club representatives can create meetings.")
        return redirect('club_detail', club_id=club.id)
    
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        scheduled_time = request.POST.get('scheduled_time')
        duration_minutes = request.POST.get('duration_minutes', 60)
        
        if title and description and scheduled_time:
            from .models import ClubMeeting
            from datetime import datetime
            import uuid
            
            meeting = ClubMeeting.objects.create(
                club=club,
                title=title,
                description=description,
                scheduled_time=datetime.fromisoformat(scheduled_time),
                duration_minutes=int(duration_minutes),
                created_by=request.user,
                meeting_link=f"/clubs/{club.id}/meeting/{uuid.uuid4().hex[:12]}/"
            )
            
            from .utils import notify_club_members
            notify_club_members(
                club,
                'general',
                f'New Club Meeting: {title}',
                f'{description}. Scheduled for {scheduled_time}',
                meeting.meeting_link
            )
            
            messages.success(request, "Club meeting created and members notified!")
            return redirect('club_detail', club_id=club.id)
    
    return render(request, 'clubs/create_meeting.html', {'club': club})


@login_required
def join_club_meeting(request, club_id, meeting_link):
    club = get_object_or_404(Club, id=club_id)
    from .models import ClubMeeting
    
    # Construct the full meeting link to match the database format
    full_meeting_link = f"/clubs/{club_id}/meeting/{meeting_link}/"
    
    try:
        # Try exact match first
        meeting = ClubMeeting.objects.get(club=club, meeting_link=full_meeting_link)
    except ClubMeeting.DoesNotExist:
        # Fallback to contains search
        try:
            meeting = ClubMeeting.objects.get(club=club, meeting_link__contains=meeting_link)
        except ClubMeeting.DoesNotExist:
            messages.error(request, "Meeting not found.")
            return redirect('club_detail', club_id=club.id)
        except ClubMeeting.MultipleObjectsReturned:
            messages.error(request, "Multiple meetings found. Please contact support.")
            return redirect('club_detail', club_id=club.id)
    
    is_member = Membership.objects.filter(user=request.user, club=club, status='approved').exists()
    is_founder = club.founders.filter(id=request.user.id).exists()
    is_representative = request.user == club.president or request.user == club.vice_president
    
    if not is_member and not is_founder and not is_representative:
        messages.error(request, "Only club members can join meetings.")
        return redirect('club_detail', club_id=club.id)
    
    # Check if meeting has been started by founder
    if meeting.status == 'ended':
        messages.error(request, "This meeting has already ended.")
        return redirect('club_detail', club_id=club.id)
    elif meeting.status != 'started':
        messages.error(request, "This meeting has not been started yet. Please wait for the organizer to start the meeting.")
        return redirect('club_detail', club_id=club.id)
    
    # Add user to participants
    meeting.participants.add(request.user)
    
    context = {
        'club': club,
        'meeting': meeting,
    }
    return render(request, 'clubs/meeting_room.html', context)


@login_required
@require_POST
def start_club_meeting(request, meeting_id):
    """Founder view to start a meeting"""
    from .models import ClubMeeting
    
    meeting = get_object_or_404(ClubMeeting, id=meeting_id)
    club = meeting.club
    
    # Check permissions - only representatives can start meetings
    representatives = club.get_representatives()
    if request.user not in representatives:
        messages.error(request, "Only club representatives can start meetings.")
        return redirect('founder_dashboard')
    
    # Start the meeting
    if meeting.start_meeting(request.user):
        # Notify all club members
        from .utils import notify_club_members
        notify_club_members(
            club,
            'general',
            f'Meeting Started: {meeting.title}',
            f'{meeting.title} has started! Join now.',
            meeting.meeting_link
        )
        messages.success(request, f"Meeting '{meeting.title}' has been started!")
        # Auto-redirect founder to the meeting room
        return redirect(meeting.meeting_link)
    else:
        messages.error(request, "Unable to start this meeting. It may have already been started or ended.")
        return redirect('founder_dashboard')


@login_required
@require_POST
def end_club_meeting(request, meeting_id):
    """Founder view to end a meeting"""
    from .models import ClubMeeting
    
    meeting = get_object_or_404(ClubMeeting, id=meeting_id)
    club = meeting.club
    
    # Check permissions - only representatives can end meetings
    representatives = club.get_representatives()
    if request.user not in representatives:
        messages.error(request, "Only club representatives can end meetings.")
        return redirect('founder_dashboard')
    
    # Check current status
    if meeting.status == 'ended':
        messages.info(request, f"Meeting '{meeting.title}' has already been ended.")
        return redirect('founder_dashboard')
    
    if meeting.status == 'scheduled':
        messages.error(request, f"Cannot end meeting '{meeting.title}' - it hasn't been started yet.")
        return redirect('founder_dashboard')
    
    # End the meeting
    if meeting.end_meeting():
        # Notify participants
        from .utils import notify_club_members
        notify_club_members(
            club,
            'general',
            f'Meeting Ended: {meeting.title}',
            f'{meeting.title} has ended. Thank you for participating!',
            f'/clubs/{club.id}/'
        )
        messages.success(request, f"Meeting '{meeting.title}' has been ended.")
    else:
        messages.error(request, f"Unable to end meeting '{meeting.title}'. Please try again.")
    
    return redirect('founder_dashboard')


@login_required
def manage_event_attendance(request, event_id):
    """Founder view to manage event attendance and check in students"""
    event = get_object_or_404(Event, id=event_id)
    club = event.club
    
    if not club.founders.filter(id=request.user.id).exists() and request.user != club.president and request.user != club.vice_president and not request.user.is_admin():
        messages.error(request, "Only club representatives can manage event attendance.")
        return redirect('club_detail', club_id=club.id)
    
    # Get all registrations for this event
    registrations = EventAttendance.objects.filter(event=event).select_related('user')
    checked_in_count = registrations.filter(checked_in_via_qr=True).count()
    
    context = {
        'event': event,
        'club': club,
        'registrations': registrations,
        'checked_in_count': checked_in_count,
    }
    return render(request, 'clubs/manage_attendance.html', context)


@login_required
@require_POST
def send_webrtc_signal(request):
    """Send WebRTC signaling data for peer connections"""
    import json
    from .models import ClubMeeting, MeetingSignal
    
    try:
        data = json.loads(request.body)
        meeting_id = data.get('meeting_id')
        signal_type = data.get('type')
        signal_data = json.dumps(data.get('data'))
        receiver_id = data.get('receiver_id')
        
        meeting = ClubMeeting.objects.get(id=meeting_id)
        
        # Authorization: verify user is a participant in the meeting
        if not meeting.participants.filter(id=request.user.id).exists():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized: not a meeting participant'}, status=403)
        
        # Verify receiver is also a participant if specified
        if receiver_id and not meeting.participants.filter(id=receiver_id).exists():
            return JsonResponse({'status': 'error', 'message': 'Receiver not a meeting participant'}, status=403)
        
        # Create the signal
        signal = MeetingSignal.objects.create(
            meeting=meeting,
            sender=request.user,
            receiver_id=receiver_id if receiver_id else None,
            signal_type=signal_type,
            signal_data=signal_data
        )
        
        return JsonResponse({'status': 'success', 'signal_id': signal.id})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@login_required
def get_webrtc_signals(request, meeting_id):
    """Get WebRTC signaling data for a meeting"""
    import json
    from .models import ClubMeeting, MeetingSignal
    
    try:
        meeting = ClubMeeting.objects.get(id=meeting_id)
        
        # Authorization: verify user is a participant in the meeting
        if not meeting.participants.filter(id=request.user.id).exists():
            return JsonResponse({'status': 'error', 'message': 'Unauthorized: not a meeting participant'}, status=403)
        
        # Get unconsumed signals for this user
        signals = MeetingSignal.objects.filter(
            meeting=meeting,
            is_consumed=False
        ).filter(
            Q(receiver=request.user) | Q(receiver__isnull=True)
        ).exclude(sender=request.user)
        
        signal_list = []
        for signal in signals:
            signal_list.append({
                'id': signal.id,
                'sender_id': signal.sender.id,
                'sender_name': signal.sender.get_full_name() or signal.sender.username,
                'type': signal.signal_type,
                'data': json.loads(signal.signal_data)
            })
            # Mark as consumed
            signal.is_consumed = True
            signal.save()
        
        # Get list of active participants
        participants = meeting.participants.all()
        participant_list = [
            {
                'id': p.id,
                'name': p.get_full_name() or p.username
            }
            for p in participants if p.id != request.user.id
        ]
        
        return JsonResponse({
            'status': 'success',
            'signals': signal_list,
            'participants': participant_list
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
