from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import WeatherRecord, Profile

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control form-control-custom', 'placeholder': 'Enter your email'}))

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'email':
                field.widget.attrs['class'] = 'form-control form-control-custom'
                field.widget.attrs['placeholder'] = f'Enter {field_name.replace("_", " ")}'

class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control form-control-custom'}))

    class Meta:
        model = User
        fields = ['username', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs['class'] = 'form-control form-control-custom'

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['location', 'bio']
        widgets = {
            'location': forms.TextInput(attrs={'class': 'form-control form-control-custom'}),
            'bio': forms.Textarea(attrs={'class': 'form-control form-control-custom', 'rows': 3}),
        }

class WeatherRecordForm(forms.ModelForm):
    class Meta:
        model = WeatherRecord
        fields = ['date', 'city', 'temperature', 'humidity', 'wind_speed', 'precipitation', 'condition']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-custom'}),
            'city': forms.TextInput(attrs={'class': 'form-control form-control-custom'}),
            'temperature': forms.NumberInput(attrs={'class': 'form-control form-control-custom', 'step': '0.1', 'placeholder': 'e.g. 24.5'}),
            'humidity': forms.NumberInput(attrs={'class': 'form-control form-control-custom', 'step': '0.1', 'placeholder': 'e.g. 60'}),
            'wind_speed': forms.NumberInput(attrs={'class': 'form-control form-control-custom', 'step': '0.1', 'placeholder': 'e.g. 15.2'}),
            'precipitation': forms.NumberInput(attrs={'class': 'form-control form-control-custom', 'step': '0.1', 'placeholder': 'e.g. 0.0'}),
            'condition': forms.Select(attrs={'class': 'form-select form-control-custom'}),
        }
