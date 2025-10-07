from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from authentication.mixins import BootstrapFormMixin
from authentication.models import EmailVerification


class OTPVerificationForm(BootstrapFormMixin, forms.Form):
    """
    Form for OTP email verification.
    
    Handles the input and validation of 6-digit OTP codes
    sent to users during email verification.
    """
    
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(
            attrs={
                'placeholder': _('Enter 6-digit code'),
                'aria-label': _('OTP Code'),
                'class': 'form-control otp-input',
                'autocomplete': 'one-time-code',
                'inputmode': 'numeric',
                'pattern': '[0-9]{6}',
                'maxlength': '6'
            }
        ),
        help_text=_('Enter the 6-digit code sent to your email address'),
        label=_('Verification Code')
    )
    
    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        # Apply Bootstrap styling to all fields
        self.apply_bootstrap_styling()
    
    def clean_otp_code(self):
        """Validate the OTP code"""
        otp_code = self.cleaned_data.get('otp_code')
        
        if not otp_code:
            raise ValidationError(_('Please enter the verification code'))
        
        # Check if it's 6 digits
        if not otp_code.isdigit() or len(otp_code) != 6:
            raise ValidationError(_('Please enter a valid 6-digit code'))
        
        # If we have a user, validate against their OTP
        if self.user:
            verification = EmailVerification.get_valid_otp(self.user, otp_code)
            if not verification:
                raise ValidationError(
                    _('Invalid or expired verification code. Please request a new one.')
                )
        
        return otp_code
    
    def verify_otp(self, user):
        """
        Verify the OTP code for a specific user.
        
        Args:
            user: The user to verify the OTP for
            
        Returns:
            bool: True if verification successful, False otherwise
        """
        if not self.is_valid():
            return False
        
        otp_code = self.cleaned_data['otp_code']
        verification = EmailVerification.get_valid_otp(user, otp_code)
        
        if verification:
            verification.mark_as_used()
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
            return True
        
        return False


class ResendOTPForm(forms.Form):
    """
    Simple form for requesting a new OTP code.
    
    This form doesn't need any fields as it just triggers
    the resend functionality.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No fields needed, just used for CSRF protection