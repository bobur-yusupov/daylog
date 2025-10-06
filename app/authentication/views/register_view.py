from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.core.mail import send_mail
from django.http import HttpResponse
from django.conf import settings
from django.core.mail.message import EmailMessage
from smtplib import SMTPException
import logging
from authentication.forms import CustomUserCreationForm
from authentication.mixins import AnonymousRequiredMixin


class RegisterView(AnonymousRequiredMixin, CreateView):
    """
    User registration view using CreateView.
    Handles both GET and POST requests for user registration.
    """

    form_class = CustomUserCreationForm
    template_name = "authentication/register.html"
    success_url = reverse_lazy("authentication:login")

    def form_valid(self, form) -> HttpResponse:
        response = super().form_valid(form)
        username = form.cleaned_data.get("username")

        messages.success(
            self.request, f"Account created for {username}! You can now log in."
        )

        # Send a welcome email to the user
        try:
            send_mail(
                subject="Welcome to DayLog!",
                message=f"Hi {username},\n\nThank you for registering at DayLog. We're excited to have you on board!",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[form.cleaned_data.get("email")],
                fail_silently=False,
            )
            logging.info(f"Welcome email sent successfully to {form.cleaned_data.get('email')}")
        except SMTPException as e:
            # Log the error but don't prevent user registration
            logging.error(f"Failed to send welcome email to {form.cleaned_data.get('email')}: {str(e)}")
            messages.warning(
                self.request, 
                "Your account was created successfully, but we couldn't send a welcome email. Please check with support if needed."
            )
        except Exception as e:
            # Catch any other email-related errors
            logging.error(f"Unexpected error sending welcome email: {str(e)}")
            messages.warning(
                self.request, 
                "Your account was created successfully, but we couldn't send a welcome email. Please check with support if needed."
            )
        
        return response

    def form_invalid(self, form) -> HttpResponse:
        if "honeypot" in form.errors:
            messages.error(self.request, "Detected spam submission.")
        else:
            messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)

    def get_success_url(self) -> str:
        next_url = self.request.GET.get("next")
        return next_url if next_url else super().get_success_url()
