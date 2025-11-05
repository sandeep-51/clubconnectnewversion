from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import User
from clubs.models import Membership
from .forms import EditProfileForm, AdminUserCreationForm

@login_required
def create_user_by_admin(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to create new users.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('password')
            user.set_password(password)
            user.save()
            messages.success(request, f'User {user.username} created successfully with the specified password.')
            return redirect('manage_users')
    else:
        form = AdminUserCreationForm()

    return render(request, 'accounts/create_user_by_admin.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('password2')
        user_type = request.POST.get('user_type', 'student')
        department = request.POST.get('department', '')
        bio = request.POST.get('bio', '')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
            return redirect('register')

        # Create the user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.user_type = user_type
        user.department = department
        user.bio = bio
        user.save()

        # Log the user in automatically
        login(request, user)
        messages.success(request, f'Welcome {username}! Your account has been created successfully.')
        return redirect('dashboard')

    return render(request, 'accounts/register.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        force_login = request.POST.get('force_login', 'false') == 'true'
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            from django.contrib.sessions.models import Session
            
            if not force_login and user.current_session_key:
                try:
                    existing_session = Session.objects.get(session_key=user.current_session_key)
                    if existing_session.get_decoded():
                        context = {
                            'username': username,
                            'show_confirmation': True
                        }
                        return render(request, 'accounts/login.html', context)
                except Session.DoesNotExist:
                    pass
            
            login(request, user)
            messages.success(request, f'Welcome back, {username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('login')

@login_required
def user_profile(request, username):
    user_profile = get_object_or_404(User, username=username)
    memberships = Membership.objects.filter(user=user_profile)
    context = {
        'user_profile': user_profile,
        'memberships': memberships,
    }
    return render(request, 'accounts/user_profile.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('user_profile', username=request.user.username)
    else:
        form = EditProfileForm(instance=request.user)
    
    return render(request, 'accounts/edit_profile.html', {'form': form})
