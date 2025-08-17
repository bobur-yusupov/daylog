from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import View
from django.http import HttpResponse, HttpRequest


class LogoutView(LoginRequiredMixin, View):
    """
    User logout view using View.
    Handles GET requests to show logout confirmation and POST requests to log out the user.
    """

    template_name: str = "authentication/logout.html"

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        return render(request, self.template_name)

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Handle POST request to log out the user.
        """
        username = request.user.username
        logout(request)
        messages.success(request, f"You have been logged out successfully, {username}.")
        return redirect("authentication:login")
