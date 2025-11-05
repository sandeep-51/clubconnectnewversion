from .models import ThemeSettings

def theme_settings(request):
    try:
        settings = ThemeSettings.objects.get(pk=1)
    except ThemeSettings.DoesNotExist:
        settings = None
    return {'theme_settings': settings}