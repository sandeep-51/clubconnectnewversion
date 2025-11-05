from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('user_type', 'profile_picture', 'department', 'bio')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('user_type', 'department')}),
    )

admin.site.register(User, CustomUserAdmin)
