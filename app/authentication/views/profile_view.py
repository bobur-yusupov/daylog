from django.views.generic import FormView
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

from authentication.forms import ProfileForm


class ProfileView(LoginRequiredMixin, FormView):
    """
    User profile view.
    Displays the user's profile information and handles profile updates.
    """
    template_name = "authentication/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("authentication:profile")

    def get_form_kwargs(self):
        """
        Override to include the user's instance in the form's initialization.
        """
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)
    
