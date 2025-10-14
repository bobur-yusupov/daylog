from .login_view import LoginView
from .logout_view import LogoutView
from .register_view import RegisterView
from .profile_view import ProfileView
from .email_verification_view import (
    EmailVerificationView,
    ResendOTPView,
    SkipVerificationView,
)
from .password_reset_view import (
    PasswordResetRequestView,
    PasswordResetOTPView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    ResendPasswordResetOTPView,
)

register_view = RegisterView.as_view()
logout_view = LogoutView.as_view()
login_view = LoginView.as_view()
profile_view = ProfileView.as_view()
email_verification_view = EmailVerificationView.as_view()
resend_otp_view = ResendOTPView.as_view()
skip_verification_view = SkipVerificationView.as_view()
password_reset_request_view = PasswordResetRequestView.as_view()
password_reset_otp_view = PasswordResetOTPView.as_view()
password_reset_confirm_view = PasswordResetConfirmView.as_view()
password_reset_complete_view = PasswordResetCompleteView.as_view()
resend_password_reset_otp_view = ResendPasswordResetOTPView.as_view()
