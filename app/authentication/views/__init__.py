from .login_view import LoginView
from .logout_view import LogoutView
from .register_view import RegisterView
from .profile_view import ProfileView

register_view = RegisterView.as_view()
logout_view = LogoutView.as_view()
login_view = LoginView.as_view()
profile_view = ProfileView.as_view()
