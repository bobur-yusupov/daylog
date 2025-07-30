from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, FormView, View
from django.urls import reverse_lazy
from .forms import CustomUserCreationForm, CustomAuthenticationForm


class RegisterView(CreateView):
    """
    User registration view using CreateView.
    Handles both GET and POST requests for user registration.
    """
    form_class = CustomUserCreationForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('authentication:login')
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect authenticated users away from registration
        if request.user.is_authenticated:
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """
        Called when valid form data has been POSTed.
        """
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        messages.success(self.request, f'Account created for {username}! You can now log in.')
        return response
    
    def form_invalid(self, form):
        """
        Called when invalid form data has been POSTed.
        """
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class LoginView(FormView):
    """
    User login view using FormView.
    Handles both GET and POST requests for user authentication.
    """
    form_class = CustomAuthenticationForm
    template_name = 'auth/login.html'
    success_url = '/'
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect authenticated users away from login
        if request.user.is_authenticated:
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        """
        Called when valid form data has been POSTed.
        """
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(self.request, username=username, password=password)
        
        if user is not None:
            login(self.request, user)
            messages.success(self.request, f'Welcome back, {username}!')
            
            # Handle 'next' parameter for redirecting after login
            next_url = self.request.GET.get('next')
            if next_url:
                return redirect(next_url)
            
            return super().form_valid(form)
        else:
            messages.error(self.request, 'Invalid username or password.')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        """
        Called when invalid form data has been POSTed.
        """
        messages.error(self.request, 'Invalid username or password.')
        return super().form_invalid(form)


class LogoutView(LoginRequiredMixin, View):
    """
    User logout view using View.
    Handles GET requests to show logout confirmation and POST requests to log out the user.
    """
    template_name = 'auth/logout.html'
    
    def get(self, request, *args, **kwargs):
        """
        Handle GET request to show logout confirmation page.
        """
        return render(request, self.template_name)
    
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to log out the user.
        """
        username = request.user.username
        logout(request)
        messages.success(request, f'You have been logged out successfully, {username}.')
        return redirect('authentication:login')


# Keep the function-based views as aliases for backward compatibility
register_view = RegisterView.as_view()
login_view = LoginView.as_view()
logout_view = LogoutView.as_view()
