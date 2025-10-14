from django.urls import path
from . import views

app_name = "authentication"

urlpatterns = [
    # Authentication views
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    # Email verification views
    path("verify-email/", views.EmailVerificationView.as_view(), name="verify_email"),
    path("resend-otp/", views.ResendOTPView.as_view(), name="resend_otp"),
    # Password reset views (OTP-based)
    path(
        "password-reset/",
        views.PasswordResetRequestView.as_view(),
        name="password_reset_request",
    ),
    path(
        "password-reset/verify/",
        views.PasswordResetOTPView.as_view(),
        name="password_reset_otp",
    ),
    path(
        "password-reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path(
        "password-reset/resend/",
        views.ResendPasswordResetOTPView.as_view(),
        name="resend_password_reset_otp",
    ),
    # Development only - remove in production
    path(
        "skip-verification/",
        views.SkipVerificationView.as_view(),
        name="skip_verification",
    ),
]
