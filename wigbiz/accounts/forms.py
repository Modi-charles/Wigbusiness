from django import forms
from .models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm

def LoginForm(request):
    username=forms.CharField()
    password=forms.CharField(
        widget=password.PasswordInput()
    )

class UserCreateForm(UserCreationForm):
    """Add a user: includes password1/password2 with Django's validation."""

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "is_active",
        )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = ""

class UserUpdateForm(forms.ModelForm):
    """Edit a user. Password is optional: leave blank to keep the current one."""

    password1 = forms.CharField(
        label="New password",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm new password",
        required=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "role",
            "is_active",
        )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = ""
            
    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1"), cleaned.get("password2")
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", "The two passwords do not match.")
            else:
                from django.contrib.auth.password_validation import validate_password

                try:
                    validate_password(p1, self.instance)
                except forms.ValidationError as e:
                    self.add_error("password1", e)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user