from django.shortcuts import redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.views.generic import FormView
from django.http import HttpResponse
from authentication.forms import CustomAuthenticationForm
from authentication.mixins import AnonymousRequiredMixin


class LoginView(AnonymousRequiredMixin, FormView):
    """
    User login view using FormView.
    Handles both GET and POST requests for user authentication.
    """

    form_class = CustomAuthenticationForm
    template_name = "authentication/login.html"
    success_url = "/"

    def form_valid(self, form) -> HttpResponse:
        """
        Called when valid form data has been POSTed.
        """
        username: str = form.cleaned_data.get("username")
        password: str = form.cleaned_data.get("password")
        user = authenticate(self.request, username=username, password=password)

        if user is not None:
            login(self.request, user)
            messages.success(self.request, f"Welcome back, {username}!")

            # Handle 'next' parameter for redirecting after login
            next_url = self.request.GET.get("next")
            if next_url:
                return redirect(next_url)

            return super().form_valid(form)
        else:
            messages.error(self.request, "Invalid username or password.")
            return self.form_invalid(form)

    def form_invalid(self, form) -> HttpResponse:
        """
        Called when invalid form data has been POSTed.
        """
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)
