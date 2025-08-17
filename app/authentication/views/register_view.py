from django.contrib import messages
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.http import HttpResponse
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
