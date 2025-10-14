from django.shortcuts import redirect
from django.contrib import messages
from django.views.generic import FormView, TemplateView
from django.http import HttpResponse
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta

from authentication.forms import (
    PasswordResetRequestForm, 
    PasswordResetOTPForm, 
    PasswordResetConfirmForm,
    ResendPasswordResetOTPForm
)
from authentication.mixins import AnonymousRequiredMixin
from authentication.services import PasswordResetService
from authentication.models import PasswordReset


class PasswordResetRequestView(AnonymousRequiredMixin, FormView):
    """
    Step 1: View for requesting a password reset OTP.
    Users enter their email address to receive a 6-digit OTP code.
    """

    form_class = PasswordResetRequestForm
    template_name = "authentication/password_reset_request.html"
    success_url = reverse_lazy("authentication:password_reset_otp")

    def form_valid(self, form) -> HttpResponse:
        """
        Process the password reset request and send OTP.
        """
        email = form.cleaned_data.get("email")
        user = PasswordResetService.get_user_by_email(email)

        if user:
            # Check for potential abuse (optional - you can enable this if needed)
            # recent_attempts = PasswordReset.objects.filter(
            #     user=user, 
            #     created_at__gte=timezone.now() - timedelta(hours=1)
            # ).count()
            # if recent_attempts >= 3:
            #     PasswordResetService.send_security_alert_email(user, "multiple_attempts")
            
            # Send password reset OTP email
            result = PasswordResetService.send_password_reset_otp(user)
            
            if result.success:
                # Store email in session for next step
                self.request.session["password_reset_email"] = email
                messages.success(
                    self.request,
                    _("We have sent a 6-digit verification code to your email address.")
                )
            else:
                messages.error(
                    self.request,
                    _("There was an error sending the verification code. Please try again later.")
                )
                return self.form_invalid(form)
        else:
            # For security reasons, don't reveal that the email doesn't exist
            # Store email in session anyway and show success message
            self.request.session["password_reset_email"] = email
            messages.success(
                self.request,
                _("We have sent a 6-digit verification code to your email address.")
            )

        return super().form_valid(form)


class PasswordResetOTPView(AnonymousRequiredMixin, FormView):
    """
    Step 2: View for verifying the OTP code sent to user's email.
    """

    form_class = PasswordResetOTPForm
    template_name = "authentication/password_reset_otp.html"
    success_url = reverse_lazy("authentication:password_reset_confirm")

    def dispatch(self, request, *args, **kwargs):
        """
        Ensure user has gone through step 1 first.
        """
        self.email = request.session.get("password_reset_email")
        if not self.email:
            messages.error(
                request,
                _("Please start the password reset process from the beginning.")
            )
            return redirect("authentication:password_reset_request")
        
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        Pass email to the form.
        """
        kwargs = super().get_form_kwargs()
        kwargs['email'] = self.email
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Add email and resend form to context.
        """
        context = super().get_context_data(**kwargs)
        context['email'] = self.email
        context['resend_form'] = ResendPasswordResetOTPForm(email=self.email)
        return context

    def form_valid(self, form) -> HttpResponse:
        """
        Verify the OTP code.
        """
        email = form.cleaned_data.get("email")
        otp_code = form.cleaned_data.get("otp_code")
        
        # Verify OTP
        password_reset = PasswordResetService.verify_otp(email, otp_code)
        
        if password_reset:
            # Store verified OTP info in session for next step
            self.request.session["password_reset_verified_email"] = email
            self.request.session["password_reset_verified_otp"] = otp_code
            
            messages.success(
                self.request,
                _("Code verified successfully. Please set your new password.")
            )
        else:
            messages.error(
                self.request,
                _("Invalid or expired verification code. Please try again.")
            )
            return self.form_invalid(form)

        return super().form_valid(form)


class PasswordResetConfirmView(AnonymousRequiredMixin, FormView):
    """
    Step 3: View for setting new password after OTP verification.
    """

    form_class = PasswordResetConfirmForm
    template_name = "authentication/password_reset_confirm.html"
    success_url = reverse_lazy("authentication:password_reset_complete")

    def dispatch(self, request, *args, **kwargs):
        """
        Ensure user has completed OTP verification first.
        """
        self.email = request.session.get("password_reset_verified_email")
        self.otp_code = request.session.get("password_reset_verified_otp")
        
        if not self.email or not self.otp_code:
            messages.error(
                request,
                _("Please complete the verification process first.")
            )
            return redirect("authentication:password_reset_request")
        
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """
        Pass email and OTP to the form.
        """
        kwargs = super().get_form_kwargs()
        kwargs['email'] = self.email
        kwargs['otp_code'] = self.otp_code
        return kwargs

    def get_context_data(self, **kwargs):
        """
        Add email to context.
        """
        context = super().get_context_data(**kwargs)
        context['email'] = self.email
        return context

    def form_valid(self, form) -> HttpResponse:
        """
        Reset the user's password.
        """
        email = form.cleaned_data.get("email")
        otp_code = form.cleaned_data.get("otp_code")
        new_password = form.cleaned_data.get("new_password")
        
        # Reset password
        success = PasswordResetService.reset_password_with_otp(email, otp_code, new_password)
        
        if success:
            # Clear session data
            self.request.session.pop("password_reset_email", None)
            self.request.session.pop("password_reset_verified_email", None)
            self.request.session.pop("password_reset_verified_otp", None)
            
            messages.success(
                self.request,
                _("Your password has been reset successfully. You can now log in with your new password.")
            )
        else:
            messages.error(
                self.request,
                _("There was an error resetting your password. Please try the process again.")
            )
            # Clear session and redirect to start
            self.request.session.pop("password_reset_email", None)
            self.request.session.pop("password_reset_verified_email", None)
            self.request.session.pop("password_reset_verified_otp", None)
            return redirect("authentication:password_reset_request")

        return super().form_valid(form)


class PasswordResetCompleteView(AnonymousRequiredMixin, TemplateView):
    """
    Step 4: View shown after password has been successfully reset.
    """
    template_name = "authentication/password_reset_complete.html"


class ResendPasswordResetOTPView(AnonymousRequiredMixin, FormView):
    """
    View for resending password reset OTP.
    """

    form_class = ResendPasswordResetOTPForm
    template_name = "authentication/password_reset_otp.html"

    def dispatch(self, request, *args, **kwargs):
        """
        Ensure user has a valid session for password reset.
        """
        self.email = request.session.get("password_reset_email")
        if not self.email:
            messages.error(
                request,
                _("Please start the password reset process from the beginning.")
            )
            return redirect("authentication:password_reset_request")
        
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form) -> HttpResponse:
        """
        Resend the OTP code.
        """
        email = form.cleaned_data.get("email")
        user = PasswordResetService.get_user_by_email(email)
        
        if user:
            # Check if we can resend
            if PasswordResetService.can_resend_otp(user):
                result = PasswordResetService.send_password_reset_otp(user)
                
                if result.success:
                    messages.success(
                        self.request,
                        _("A new verification code has been sent to your email.")
                    )
                else:
                    messages.error(
                        self.request,
                        _("There was an error sending the verification code. Please try again later.")
                    )
            else:
                messages.warning(
                    self.request,
                    _("Please wait before requesting a new code.")
                )
        else:
            # For security, show success even if user doesn't exist
            messages.success(
                self.request,
                _("A new verification code has been sent to your email.")
            )
        
        # Redirect back to OTP verification page
        return redirect("authentication:password_reset_otp")