from django.contrib import admin
from .models import Club, Event, Membership, Message, Announcement

admin.site.register(Club)
admin.site.register(Event)
admin.site.register(Membership)
admin.site.register(Message)
admin.site.register(Announcement)
