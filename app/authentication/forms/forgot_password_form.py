from django import forms
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from authentication.mixins import BootstrapFormMixin
from authentication.models import User


class PasswordResetRequestForm(BootstrapFormMixin, forms.Form):
    """
    Form for requesting a password reset OTP.
    """
    email = forms.EmailField(
        label=_("Email Address"),
        max_length=254,
        widget=forms.EmailInput(attrs={
            "placeholder": _("Enter your email address"),
            "autocomplete": "email",
        }),
        help_text=_("Enter the email address associated with your account.")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styling()

    def clean_email(self):
        """
        Validate and normalize the email address.
        Note: For security reasons, we don't reveal if the email exists or not
        in the actual view, but we validate it here for proper form handling.
        """
        email = self.cleaned_data.get("email")
        if email:
            # Convert to lowercase for consistency
            email = email.lower().strip()
        return email


class PasswordResetOTPForm(BootstrapFormMixin, forms.Form):
    """
    Form for verifying the OTP sent for password reset.
    """
    email = forms.EmailField(
        label=_("Email Address"),
        max_length=254,
        widget=forms.EmailInput(attrs={
            "placeholder": _("Enter your email address"),
            "autocomplete": "email",
            "readonly": True,
        }),
    )
    otp_code = forms.CharField(
        label=_("Verification Code"),
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            "placeholder": _("Enter 6-digit code"),
            "autocomplete": "one-time-code",
            "inputmode": "numeric",
            "pattern": "[0-9]{6}",
            "maxlength": "6",
        }),
        help_text=_("Enter the 6-digit code sent to your email address.")
    )

    def __init__(self, *args, **kwargs):
        # Extract email from kwargs if provided
        self.email = kwargs.pop('email', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styling()
        
        # Pre-populate email field if provided
        if self.email:
            self.fields['email'].initial = self.email

    def clean_otp_code(self):
        """
        Validate the OTP code format.
        """
        otp_code = self.cleaned_data.get("otp_code")
        if otp_code:
            # Ensure it's 6 digits
            if not otp_code.isdigit() or len(otp_code) != 6:
                raise forms.ValidationError(_("Please enter a valid 6-digit code."))
        return otp_code


class PasswordResetConfirmForm(BootstrapFormMixin, forms.Form):
    """
    Form for setting new password after OTP verification.
    """
    email = forms.EmailField(
        widget=forms.HiddenInput()
    )
    otp_code = forms.CharField(
        widget=forms.HiddenInput()
    )
    new_password = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(attrs={
            "placeholder": _("Enter new password"),
            "autocomplete": "new-password",
        }),
        help_text=_(
            "Your password must contain at least 8 characters and cannot be entirely numeric."
        )
    )
    confirm_password = forms.CharField(
        label=_("Confirm New Password"),
        widget=forms.PasswordInput(attrs={
            "placeholder": _("Confirm new password"),
            "autocomplete": "new-password",
        }),
    )

    def __init__(self, *args, **kwargs):
        # Extract email and otp_code from kwargs if provided
        self.email = kwargs.pop('email', None)
        self.otp_code = kwargs.pop('otp_code', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styling()
        
        # Pre-populate hidden fields if provided
        if self.email:
            self.fields['email'].initial = self.email
        if self.otp_code:
            self.fields['otp_code'].initial = self.otp_code

    def clean_new_password(self):
        """
        Validate the new password using Django's password validators.
        """
        password = self.cleaned_data.get("new_password")
        if password:
            validate_password(password)
        return password

    def clean(self):
        """
        Validate that both passwords match.
        """
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError(_("The two password fields must match."))
        
        return cleaned_data


class ResendPasswordResetOTPForm(BootstrapFormMixin, forms.Form):
    """
    Form for resending password reset OTP.
    """
    email = forms.EmailField(
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        self.email = kwargs.pop('email', None)
        super().__init__(*args, **kwargs)
        
        if self.email:
            self.fields['email'].initial = self.email


# Legacy form name for backward compatibility
ResetPasswordForm = PasswordResetConfirmForm
