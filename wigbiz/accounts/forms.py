from django import forms
from django.contrib.auth.forms import AuthenticationForm
def LoginForm(request):
    username=forms.CharField()
    password=forms.CharField(
        widget=password.PasswordInput()
    )