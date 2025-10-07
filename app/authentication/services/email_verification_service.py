from django.core.mail import EmailMultiAlternatives, BadHeaderError
from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.conf import settings
from django.utils.html import strip_tags
from django.db import IntegrityError, DatabaseError

import logging
from dataclasses import dataclass
from typing import Optional
from smtplib import SMTPException
from socket import gaierror
from authentication.models import EmailVerification

from authentication.exceptions import EmailDeliveryError, TemplateRenderingError

logger = logging.getLogger(__name__)

@dataclass
class EmailVerificationResult:
    success: bool
    verification: Optional[EmailVerification] = None
    error_message: Optional[str] = None


class EmailVerificationService:
    """
    Service class to handle email verification operations.
    
    This service encapsulates all the logic for sending OTP emails
    and managing email verification workflow.
    """
    OTP_TEMPLATE_HTML = 'authentication/emails/otp_verification.html'
    OTP_TEMPLATE_TEXT = 'authentication/emails/otp_verification.txt'
    SITE_NAME = 'DayLog'
    OTP_EXPIRY_MINUTES = getattr(settings, 'OTP_EXPIRY_MINUTES', 10)

    @staticmethod
    def send_verification_email(user) -> EmailVerificationResult:
        """
        Creates an EmailVerification record and sends the OTP to the user's email.
        """
        try:
            verification = EmailVerification.create_for_user(user)
            EmailVerificationService._send_otp_email(user, verification)

            logger.info("OTP email sent successfully", extra={"user_id": user.id, "email": user.email})
            return EmailVerificationResult(success=True, verification=verification)

        except (IntegrityError, DatabaseError):
            logger.exception("Database error while creating verification", extra={"user_id": user.id})
            return EmailVerificationResult(success=False, error_message="Database error during verification creation")

        except (TemplateRenderingError, EmailDeliveryError) as e:
            return EmailVerificationResult(success=False, error_message=str(e))

        except Exception:
            logger.exception("Unexpected error while sending verification email", extra={"user_id": user.id})
            return EmailVerificationResult(success=False, error_message="Unexpected error during email sending")

    @staticmethod
    def verify_email_with_otp(user, otp_code: str) -> EmailVerificationResult:
        try:
            verification = EmailVerification.get_valid_otp(user, otp_code)
            if not verification:
                return EmailVerificationResult(success=False, error_message="Invalid or expired verification code")

            verification.mark_as_used()
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])

            logger.info("Email verified successfully", extra={"user": user.username})
            return EmailVerificationResult(success=True)

        except (IntegrityError, DatabaseError) as e:
            logger.exception("Database error verifying OTP", extra={"user": user.id})
            return EmailVerificationResult(success=False, error_message="Database error during verification")

        except Exception as e:
            logger.exception("Unexpected verification error", extra={"user": user.id})
            return EmailVerificationResult(success=False, error_message="Unexpected error during OTP verification")

    @staticmethod
    def resend_verification_email(user) -> EmailVerificationResult:
        """
        Marks previous OTPs as used and sends a new verification email.
        """
        try:
            EmailVerification.objects.filter(user=user, is_used=False).update(is_used=True)
            return EmailVerificationService.send_verification_email(user)

        except (IntegrityError, DatabaseError) as e:
            logger.exception("Database error during resend", extra={"user": user.id})
            return EmailVerificationResult(success=False, error_message="Database error during resend")

        except Exception as e:
            logger.exception("Unexpected resend error", extra={"user": user.id})
            return EmailVerificationResult(success=False, error_message="Unexpected error during resend")

    # ------------------------
    # Internal helper methods
    # ------------------------

    @staticmethod
    def _render_email_templates(context):
        html_content = render_to_string(EmailVerificationService.OTP_TEMPLATE_HTML, context)
        text_content = render_to_string(EmailVerificationService.OTP_TEMPLATE_TEXT, context)
        return html_content, text_content
        
    @staticmethod
    def _deliver_email(subject: str, text_content: str, html_content: str, recipient: str) -> None:
        """Sends the rendered email."""
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient]
        )
        email.attach_alternative(html_content, "text/html")
        email.send()

    @staticmethod
    def _send_otp_email(user, verification) -> None:
        """
        Internal method to send OTP email to the user.
        
        Args:
            user: User instance to send email to
            verification: EmailVerification instance containing the OTP code
        """
        subject = f"Your {EmailVerificationService.SITE_NAME} verification code: {verification.otp_code}"
        context = {
            'user': user,
            'otp_code': verification.otp_code,
            'expires_in_minutes': getattr(settings, 'OTP_EXPIRY_MINUTES', 10),
            'site_name': EmailVerificationService.SITE_NAME,
        }
        try:
            html_content, text_content = EmailVerificationService._render_email_templates(context)
            EmailVerificationService._deliver_email(subject, text_content, html_content, user.email)

        except TemplateDoesNotExist as e:
            logger.error("Email template not found: %s", e)
            raise TemplateRenderingError("Email template missing or misconfigured") from e
        except TemplateSyntaxError as e:
            logger.error("Email template syntax error: %s", e)
            raise TemplateRenderingError("Email template syntax issue") from e
        except (SMTPException, BadHeaderError, gaierror) as e:
            logger.error("Failed to send OTP email: %s", e)
            raise EmailDeliveryError("Failed to send verification email") from e
