from django import forms
from .models import User
from django.contrib.auth.forms import AuthenticationForm
def LoginForm(request):
    username=forms.CharField()
    password=forms.CharField(
        widget=password.PasswordInput()
    )
class UserForm(forms.ModelForm):
    class meta:
        model=User
        fields=['phone','role','first_name','last_name','email']
