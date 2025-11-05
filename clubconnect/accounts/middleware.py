from django.utils import timezone
from django.core.cache import cache
from .models import User

class UpdateLastSeenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            cache_key = f'last_seen_update_{request.user.pk}'
            last_update = cache.get(cache_key)
            
            now = timezone.now()
            if not last_update or (now - last_update).seconds > 30:
                User.objects.filter(pk=request.user.pk).update(last_seen=now)
                cache.set(cache_key, now, 60)
        
        response = self.get_response(request)
        return response