from django.db import models

class ThemeSettings(models.Model):
    primary_color = models.CharField(max_length=7, default='#007bff')
    secondary_color = models.CharField(max_length=7, default='#6c757d')

    def __str__(self):
        return 'Theme Settings'