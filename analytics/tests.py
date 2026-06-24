from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from analytics.models import WeatherRecord, Profile
import datetime

class WeatherAnalyticsTests(TestCase):
    def setUp(self):
        # Create standard user
        self.user = User.objects.create_user(username='testuser', password='password123', email='test@example.com')
        self.client = Client()

    def test_user_signup(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'newpassword123',
            'password2': 'newpassword123'
        })
        # Signup redirects on success
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302) # Redirects to login

    def test_dashboard_with_login(self):
        self.client.login(username='testuser', password='password123')
        
        # Add sample records
        WeatherRecord.objects.create(
            date=datetime.date(2026, 6, 1),
            temperature=30.0,
            humidity=60.0,
            wind_speed=10.0,
            precipitation=0.0,
            condition='Sunny'
        )
        
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weather Dashboard")
        self.assertContains(response, "30.0°C") # average temp

    def test_weather_record_crud(self):
        self.client.login(username='testuser', password='password123')
        
        # Test Create
        response = self.client.post(reverse('record_add'), {
            'date': '2026-06-25',
            'temperature': '25.5',
            'humidity': '55.0',
            'wind_speed': '12.0',
            'precipitation': '2.5',
            'condition': 'Rainy'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(WeatherRecord.objects.filter(date='2026-06-25').exists())
        
        # Test Edit
        record = WeatherRecord.objects.get(date='2026-06-25')
        response = self.client.post(reverse('record_edit', args=[record.pk]), {
            'date': '2026-06-25',
            'temperature': '28.0', # Changed
            'humidity': '55.0',
            'wind_speed': '12.0',
            'precipitation': '2.5',
            'condition': 'Sunny' # Changed
        })
        self.assertEqual(response.status_code, 302)
        record.refresh_from_db()
        self.assertEqual(record.temperature, 28.0)
        self.assertEqual(record.condition, 'Sunny')

    def test_chart_data_endpoint(self):
        self.client.login(username='testuser', password='password123')
        WeatherRecord.objects.create(
            date=datetime.date(2026, 6, 1),
            temperature=30.0,
            humidity=60.0,
            wind_speed=10.0,
            precipitation=0.0,
            condition='Sunny'
        )
        response = self.client.get(reverse('chart_data'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('temps', response.json())
