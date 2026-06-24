from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class WeatherRecord(models.Model):
    CONDITION_CHOICES = [
        ('Sunny', 'Sunny'),
        ('Rainy', 'Rainy'),
        ('Cloudy', 'Cloudy'),
        ('Snowy', 'Snowy'),
        ('Stormy', 'Stormy'),
        ('Windy', 'Windy'),
    ]
    
    date = models.DateField(unique=True)
    temperature = models.FloatField(help_text="Temperature in Celsius")
    humidity = models.FloatField(help_text="Humidity percentage")
    wind_speed = models.FloatField(help_text="Wind speed in km/h")
    precipitation = models.FloatField(help_text="Precipitation in mm")
    condition = models.CharField(max_length=50, choices=CONDITION_CHOICES)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} - {self.condition} ({self.temperature}°C)"

    class Meta:
        ordering = ['-date']

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=100, blank=True, default="New York")
    bio = models.TextField(max_length=500, blank=True, default="Weather Enthusiast")
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# Signals to automatically create/update profile
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
