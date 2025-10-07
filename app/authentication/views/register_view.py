from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse
from django.shortcuts import redirect
import logging

from authentication.forms import CustomUserCreationForm
from authentication.mixins import AnonymousRequiredMixin
from authentication.services import EmailVerificationService

logger = logging.getLogger(__name__)


class RegisterView(AnonymousRequiredMixin, CreateView):
    """
    User registration view with email verification.
    
    After successful registration, users are redirected to email verification
    where they need to enter a 6-digit OTP code sent to their email.
    """

    form_class = CustomUserCreationForm
    template_name = "authentication/register.html"
    success_url = reverse_lazy("authentication:verify_email")

    def form_valid(self, form) -> HttpResponse:
        """
        Handle successful user registration.
        
        Creates the user account and initiates email verification process.
        Note: We don't log in the user automatically - they must verify their email first.
        """
        # Create the user but don't log them in automatically
        self.object = form.save()
        user = self.object
        username = form.cleaned_data.get("username")
        
        # Store user ID in session for verification process
        self.request.session['pending_verification_user_id'] = str(user.id)
        
        # Send OTP verification email
        result = EmailVerificationService.send_verification_email(user)
        
        if result.success:
            messages.success(
                self.request,
                f"Account created for {username}! Please check your email for the verification code."
            )
            logger.info(f"User {username} registered successfully and OTP sent to {user.email}")
        else:
            # If email sending fails, still allow registration but show warning
            messages.warning(
                self.request,
                f"Account created for {username}, but we couldn't send the verification email. "
                "Please try to resend the verification code."
            )
            logger.error(f"User {username} registered but OTP email failed: {result.error_message}")
        
        # Redirect to email verification page (not logging in the user)
        return redirect(self.get_success_url())

    def form_invalid(self, form) -> HttpResponse:
        """Handle registration form validation errors"""
        if "honeypot" in form.errors:
            messages.error(self.request, "Detected spam submission.")
            logger.warning(f"Spam submission detected from IP: {self.request.META.get('REMOTE_ADDR')}")
        else:
            messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self) -> str:
        """Return URL to redirect after successful registration"""
        # Always redirect to email verification after registration
        return reverse('authentication:verify_email')
