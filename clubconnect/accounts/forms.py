from django import forms
from .models import User

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'bio', 'profile_picture']

class AdminUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        }),
        label='Password',
        help_text='Password must be at least 8 characters long'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        }),
        label='Confirm Password'
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'user_type', 'department']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
            'user_type': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter department'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError("Passwords do not match!")
            if len(password) < 8:
                raise forms.ValidationError("Password must be at least 8 characters long!")
        
        return cleaned_data