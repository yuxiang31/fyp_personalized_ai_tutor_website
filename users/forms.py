# forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model, authenticate
import re

User = get_user_model()

# Shared validator to ensure names start with a letter and only contain letters/spaces
def _validate_person_name(value: str, label: str) -> str:
    value = (value or '').strip()
    if not value:
        raise forms.ValidationError(f"{label} cannot be blank.")
    # Must start with a letter (A-Z or a-z)
    if not re.match(r"^[A-Za-z]", value):
        raise forms.ValidationError(f"{label} must start with a letter.")
    # Only letters and spaces allowed in the whole string
    invalid_chars = sorted(set(re.findall(r"[^A-Za-z\s]", value)))
    if invalid_chars:
        bad = ' '.join(invalid_chars)
        raise forms.ValidationError(
            f"{label} can only contain letters and spaces. Remove these characters: {bad}"
        )
    return value

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email','learning_preference', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

    # Ensure first and last names start with a letter and contain valid characters
    def clean_first_name(self):
        return _validate_person_name(self.cleaned_data.get('first_name'), 'First name')

    def clean_last_name(self):
        return _validate_person_name(self.cleaned_data.get('last_name'), 'Last name')


class CustomAuthenticationForm(AuthenticationForm):
    """Authentication form with clearer, more specific error messages.

    - Validates email format using EmailField
    - If email is not registered: error on email field
    - If password is wrong: error on password field
    - Keeps inactive account check via confirm_login_allowed
    """

    # Use EmailField to get proper email validation and browser email keyboard on mobile
    username = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={'autofocus': True}),
    )

    def clean(self):
        # Field-level validation (EmailField format, required) runs before this
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        # If either missing, rely on field-level required errors
        if not email or not password:
            return self.cleaned_data

        # Check if the email exists first to tailor the message
        user = User._default_manager.filter(email__iexact=email).first()
        if not user:
            self.add_error('username', 'No account found with this email.')
            return self.cleaned_data

        # Email exists; check password correctness specifically
        if not user.check_password(password):
            self.add_error('password', 'The password you entered is incorrect.')
            return self.cleaned_data

        # Password is correct — ensure the account is allowed to log in
        self.confirm_login_allowed(user)
        # Cache the user for the view's form.get_user()
        self.user_cache = user
        return self.cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    """Allow updating first name, last name, and learning preference; show email read-only."""
    email = forms.EmailField(disabled=True, required=False, label='Email')

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'learning_preference',
            'email',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].label = 'First name'
        self.fields['last_name'].label = 'Last name'
        self.fields['learning_preference'].label = 'Learning preference'
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False

    def _validate_name(self, value: str, label: str) -> str:
        # Delegate to shared validator to keep behavior consistent with registration form
        return _validate_person_name(value, label)

    def clean_first_name(self):
        return self._validate_name(self.cleaned_data.get('first_name'), 'First name')

    def clean_last_name(self):
        return self._validate_name(self.cleaned_data.get('last_name'), 'Last name')

