from django.core.mail import EmailMultiAlternatives, BadHeaderError
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.conf import settings
from django.db import IntegrityError, DatabaseError

import logging
from dataclasses import dataclass
from typing import Optional
from smtplib import SMTPException
from socket import gaierror
from authentication.models import PasswordReset, User

from authentication.exceptions import EmailDeliveryError, TemplateRenderingError

logger = logging.getLogger(__name__)


@dataclass
class PasswordResetResult:
    success: bool
    password_reset: Optional[PasswordReset] = None
    error_message: Optional[str] = None


class PasswordResetService:
    """
    Service class to handle password reset operations using OTP.

    This service encapsulates all the logic for sending password reset OTP emails
    and managing password reset workflow.
    """

    OTP_TEMPLATE_HTML = "authentication/emails/password_reset_otp.html"
    OTP_TEMPLATE_TEXT = "authentication/emails/password_reset_otp.txt"
    CONFIRMATION_TEMPLATE_HTML = (
        "authentication/emails/password_reset_confirmation.html"
    )
    CONFIRMATION_TEMPLATE_TEXT = "authentication/emails/password_reset_confirmation.txt"
    SITE_NAME = "DayLog"
    OTP_EXPIRY_MINUTES = getattr(settings, "OTP_EXPIRY_MINUTES", 10)

    @staticmethod
    def send_password_reset_otp(user) -> PasswordResetResult:
        """
        Creates a PasswordReset record and sends the OTP to the user's email.
        """
        try:
            password_reset = PasswordReset.create_for_user(user)
            PasswordResetService._send_otp_email(user, password_reset)

            logger.info(
                "Password reset OTP email sent successfully",
                extra={"user_id": user.id, "email": user.email},
            )

            return PasswordResetResult(success=True, password_reset=password_reset)

        except (EmailDeliveryError, TemplateRenderingError) as e:
            logger.error(
                "Failed to send password reset OTP email",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "error": str(e),
                },
            )
            return PasswordResetResult(success=False, error_message=str(e))

        except (IntegrityError, DatabaseError) as e:
            logger.error(
                "Database error while creating password reset",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "error": str(e),
                },
            )
            return PasswordResetResult(
                success=False, error_message="Failed to create password reset request"
            )

        except Exception as e:
            logger.error(
                "Unexpected error during password reset process",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "error": str(e),
                },
            )
            return PasswordResetResult(
                success=False, error_message="An unexpected error occurred"
            )

    @staticmethod
    def _send_otp_email(user, password_reset):
        """
        Send the password reset email with the OTP code.
        """
        try:
            context = {
                "user": user,
                "otp_code": password_reset.otp_code,
                "site_name": PasswordResetService.SITE_NAME,
                "expiry_minutes": PasswordResetService.OTP_EXPIRY_MINUTES,
            }

            # Render email templates
            html_content = render_to_string(
                PasswordResetService.OTP_TEMPLATE_HTML, context
            )
            text_content = render_to_string(
                PasswordResetService.OTP_TEMPLATE_TEXT, context
            )

            subject = f"Password Reset Code - {PasswordResetService.SITE_NAME}"

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.attach_alternative(html_content, "text/html")

            # Send email
            msg.send()

        except (TemplateDoesNotExist, TemplateSyntaxError) as e:
            logger.error(f"Template error: {e}")
            raise TemplateRenderingError(f"Failed to render email template: {e}")

        except (SMTPException, gaierror, BadHeaderError) as e:
            logger.error(f"Email delivery error: {e}")
            raise EmailDeliveryError(f"Failed to send email: {e}")

        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            raise EmailDeliveryError(f"Unexpected error occurred: {e}")

    @staticmethod
    def _send_confirmation_email(user):
        """
        Send a confirmation email after password has been successfully reset.
        """
        try:
            from django.utils import timezone

            context = {
                "user": user,
                "site_name": PasswordResetService.SITE_NAME,
                "reset_time": timezone.now(),
            }

            # Render email templates
            html_content = render_to_string(
                PasswordResetService.CONFIRMATION_TEMPLATE_HTML, context
            )
            text_content = render_to_string(
                PasswordResetService.CONFIRMATION_TEMPLATE_TEXT, context
            )

            subject = f"Password Reset Confirmation - {PasswordResetService.SITE_NAME}"

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.attach_alternative(html_content, "text/html")

            # Send email
            msg.send()

        except (TemplateDoesNotExist, TemplateSyntaxError) as e:
            logger.error(f"Template error in confirmation email: {e}")
            # Don't raise error for confirmation email - it's not critical

        except (SMTPException, gaierror, BadHeaderError) as e:
            logger.error(f"Email delivery error for confirmation: {e}")
            # Don't raise error for confirmation email - it's not critical

        except Exception as e:
            logger.error(f"Unexpected error sending confirmation email: {e}")
            # Don't raise error for confirmation email - it's not critical

    @staticmethod
    def send_security_alert_email(user, alert_type="suspicious_activity"):
        """
        Send a security alert email for suspicious password reset activity.

        Args:
            user: The user to send the alert to
            alert_type: Type of alert ('suspicious_activity', 'multiple_attempts', etc.)
        """
        try:
            from django.utils import timezone

            subject = f"Security Alert - {PasswordResetService.SITE_NAME}"

            # Simple text email for security alerts
            message = f"""
Security Alert - {PasswordResetService.SITE_NAME}

Hello {user.first_name or user.username},

We detected suspicious password reset activity on your account ({user.email}) at {timezone.now().strftime('%B %d, %Y at %I:%M %p %Z')}.

If this was you, you can safely ignore this email. If you didn't attempt to reset your password, please:

1. Check your account security
2. Change your password if needed
3. Contact our support team if you have concerns

For your security, we recommend:
- Using a strong, unique password
- Not sharing your login credentials
- Logging out from shared devices

Best regards,
The {PasswordResetService.SITE_NAME} Team

---
This is an automated security alert. Please do not reply to this email.
            """.strip()

            # Create and send email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
            )
            msg.send()

            logger.info(
                "Security alert email sent",
                extra={
                    "user_id": user.id,
                    "email": user.email,
                    "alert_type": alert_type,
                },
            )

        except Exception as e:
            logger.error(
                "Failed to send security alert email",
                extra={"user_id": user.id, "email": user.email, "error": str(e)},
            )
            # Don't raise error for security alert email - it's not critical

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        Get a user by email address.

        Args:
            email: The email address to search for

        Returns:
            User instance if found, None otherwise
        """
        try:
            return User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return None

    @staticmethod
    def verify_otp(email: str, otp_code: str) -> Optional[PasswordReset]:
        """
        Verify the OTP code for password reset.

        Args:
            email: The user's email address
            otp_code: The OTP code to verify

        Returns:
            PasswordReset instance if OTP is valid, None otherwise
        """
        try:
            user = PasswordResetService.get_user_by_email(email)
            if not user:
                return None

            # Get the most recent unused password reset for this user
            password_reset = (
                PasswordReset.objects.filter(user=user, is_used=False)
                .order_by("-created_at")
                .first()
            )

            if not password_reset:
                return None

            # Increment attempts
            password_reset.increment_attempts()

            # Check if OTP matches and is still valid
            if password_reset.otp_code == otp_code and password_reset.is_valid():
                return password_reset

            return None

        except Exception as e:
            logger.error(
                "Error during OTP verification",
                extra={"email": email, "error": str(e)},
            )
            return None

    @staticmethod
    def reset_password_with_otp(email: str, otp_code: str, new_password: str) -> bool:
        """
        Reset a user's password using a valid OTP.

        Args:
            email: The user's email address
            otp_code: The OTP code
            new_password: The new password to set

        Returns:
            bool: True if password was reset successfully, False otherwise
        """
        try:
            password_reset = PasswordResetService.verify_otp(email, otp_code)
            if not password_reset:
                return False

            # Update the user's password
            user = password_reset.user
            user.set_password(new_password)
            user.save()

            # Mark the OTP as used
            password_reset.mark_as_used()

            # Send confirmation email if enabled
            confirmation_enabled = getattr(
                settings, "PASSWORD_RESET_CONFIRMATION_EMAIL_ENABLED", True
            )
            if confirmation_enabled:
                try:
                    PasswordResetService._send_confirmation_email(user)
                    logger.info(
                        "Password reset completed successfully with confirmation email sent",
                        extra={"user_id": user.id, "email": user.email},
                    )
                except Exception as e:
                    logger.warning(
                        "Password reset completed but confirmation email failed",
                        extra={
                            "user_id": user.id,
                            "email": user.email,
                            "error": str(e),
                        },
                    )
            else:
                logger.info(
                    "Password reset completed successfully (confirmation email disabled)",
                    extra={"user_id": user.id, "email": user.email},
                )

            return True

        except Exception as e:
            logger.error(
                "Error during password reset",
                extra={"email": email, "error": str(e)},
            )
            return False

    @staticmethod
    def can_resend_otp(user) -> bool:
        """
        Check if a new OTP can be sent to the user.

        Args:
            user: The user requesting OTP resend

        Returns:
            bool: True if OTP can be resent, False otherwise
        """
        from django.utils import timezone

        # Get the most recent password reset for this user
        recent_reset = (
            PasswordReset.objects.filter(user=user).order_by("-created_at").first()
        )

        if not recent_reset:
            return True

        # Check if enough time has passed (60 seconds by default)
        resend_interval = getattr(settings, "OTP_RESEND_INTERVAL_SECONDS", 60)
        time_since_last = (timezone.now() - recent_reset.created_at).total_seconds()

        return time_since_last >= resend_interval
