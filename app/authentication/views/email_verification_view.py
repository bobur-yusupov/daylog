from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
import logging

from authentication.forms import OTPVerificationForm, ResendOTPForm
from authentication.services import EmailVerificationService
from authentication.mixins import AnonymousRequiredMixin

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailVerificationView(AnonymousRequiredMixin, FormView):
    """
    View to handle email verification with OTP code.

    This view handles both GET and POST requests for OTP verification.
    Users are redirected here after registration to verify their email.
    """

    template_name = "authentication/email_verification.html"
    form_class = OTPVerificationForm
    success_url = reverse_lazy("authentication:login")

    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to get user from session"""
        user_id = request.session.get("pending_verification_user_id")
        if not user_id:
            messages.error(
                request, "No pending verification found. Please register again."
            )
            return redirect("authentication:register")

        try:
            self.user = User.objects.get(id=user_id, is_email_verified=False)
        except User.DoesNotExist:
            messages.error(
                request, "Invalid verification session. Please register again."
            )
            return redirect("authentication:register")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Pass user to form"""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.user
        return kwargs

    def get_context_data(self, **kwargs):
        """Add user and resend form to context"""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "user": self.user,
                "resend_form": ResendOTPForm(),
                "masked_email": self._mask_email(self.user.email),
            }
        )
        return context

    def form_valid(self, form):
        """Handle valid OTP verification"""
        success = form.verify_otp(self.user)

        if success:
            # Clear the session
            if "pending_verification_user_id" in self.request.session:
                del self.request.session["pending_verification_user_id"]

            messages.success(
                self.request,
                f"Email verified successfully! You can now log in to your DayLog account, {self.user.first_name or self.user.username}!",
            )
            logger.info(f"User {self.user.username} successfully verified their email")
            return super().form_valid(form)
        else:
            messages.error(
                self.request, "Invalid or expired verification code. Please try again."
            )
            return self.form_invalid(form)

    def form_invalid(self, form):
        """Handle invalid OTP verification"""
        messages.error(
            self.request, "Please check your verification code and try again."
        )
        return super().form_invalid(form)

    @staticmethod
    def _mask_email(email):
        """Mask email address for display (e.g., j***@example.com)"""
        if "@" not in email:
            return email

        username, domain = email.split("@", 1)
        if len(username) <= 3:
            masked_username = username[0] + "*" * (len(username) - 1)
        else:
            masked_username = username[0] + "*" * (len(username) - 2) + username[-1]

        return f"{masked_username}@{domain}"


class ResendOTPView(View):
    """
    View to handle resending OTP verification codes.

    This view only accepts POST requests and returns JSON responses
    for AJAX calls from the frontend.
    """

    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        """Handle OTP resend request"""
        user_id = request.session.get("pending_verification_user_id")
        if not user_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "No pending verification found. Please register again.",
                },
                status=400,
            )

        try:
            user = User.objects.get(id=user_id, is_email_verified=False)
        except User.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Invalid verification session. Please register again.",
                },
                status=400,
            )

        # Resend OTP
        result = EmailVerificationService.resend_verification_email(user)

        if result.success:
            logger.info(f"OTP resent successfully for user {user.username}")
            return JsonResponse(
                {
                    "success": True,
                    "message": f"A new verification code has been sent to {EmailVerificationView._mask_email(user.email)}",
                }
            )
        else:
            logger.error(
                f"Failed to resend OTP for user {user.username}: {result.error_message}"
            )
            return JsonResponse(
                {
                    "success": False,
                    "message": result.error_message
                    or "Failed to resend verification code. Please try again.",
                },
                status=500,
            )

    def get(self, request, *args, **kwargs):
        """Redirect GET requests to verification page"""
        return redirect("authentication:verify_email")


class SkipVerificationView(View):
    """
    Temporary view to allow users to skip email verification during development.

    WARNING: This should be removed in production!
    """

    def post(self, request, *args, **kwargs):
        """Skip email verification (development only)"""
        user_id = request.session.get("pending_verification_user_id")
        if not user_id:
            messages.error(request, "No pending verification found.")
            return redirect("authentication:register")

        try:
            user = User.objects.get(id=user_id)
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])

            # Clear the session
            if "pending_verification_user_id" in request.session:
                del request.session["pending_verification_user_id"]

            messages.warning(
                request,
                f"Email verification skipped for {user.username}. This is only allowed in development!",
            )
            logger.warning(f"Email verification skipped for user {user.username}")

            return redirect("authentication:login")

        except User.DoesNotExist:
            messages.error(request, "Invalid verification session.")
            return redirect("authentication:register")
