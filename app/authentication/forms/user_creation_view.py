from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model, password_validation
from django.utils.translation import gettext_lazy as _
from authentication.mixins import BootstrapFormMixin

User = get_user_model()


class CustomUserCreationForm(BootstrapFormMixin, UserCreationForm):
    """
    Custom user registration form with Bootstrap styling and spam protection.
    """

    honeypot = forms.CharField(
        required=False, widget=forms.HiddenInput, label=_("Honeypot Field")
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": _("Enter your email"),
                "aria-label": _("Email"),
            }
        ),
        help_text=_("Enter a valid email address"),
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("First name"),
                "aria-label": _("First name"),
            }
        ),
        help_text=_("Enter your first name"),
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Last name"),
                "aria-label": _("Last name"),
            }
        ),
        help_text=_("Enter your last name"),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply Bootstrap styling to all fields
        self.apply_bootstrap_styling()

        # Set placeholders for inherited fields
        self.fields["username"].widget.attrs.update(
            {"placeholder": _("Choose a username")}
        )
        self.fields["password1"].widget.attrs.update(
            {"placeholder": _("Enter password")}
        )
        self.fields["password2"].widget.attrs.update(
            {"placeholder": _("Confirm password")}
        )

    def clean_honeypot(self):
        honeypot = self.cleaned_data.get("honeypot")
        if honeypot:
            raise forms.ValidationError(_("Detected spam submission."))
        return honeypot

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with that email already exists."))
        return email

    def clean_password1(self):
        """Validate the first password field."""
        password1 = self.cleaned_data.get("password1")
        if password1:
            password_validation.validate_password(password1, self.instance)
        return password1

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user
