from django import forms
from .models import Club, Event, Membership, Announcement

class ClubForm(forms.ModelForm):
    class Meta:
        model = Club
        fields = ['name', 'short_description', 'long_description', 'domain_tags', 'faculty_advisor', 'logo']
        widgets = {
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'long_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'domain_tags': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. technology, sports, arts'}),
        }

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'location', 'start_time', 'end_time', 'image']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }

class ClubRegistrationForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Why do you want to join this club?",
        required=True
    )
    
    skills = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="What skills or interests do you have that are relevant to this club?",
        required=True
    )

class MessageForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Message",
        required=True
    )

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }