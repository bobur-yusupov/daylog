from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging
from authentication.models import EmailVerification


logger = logging.getLogger(__name__)


class EmailVerificationService:
    """
    Service class to handle email verification operations.
    
    This service encapsulates all the logic for sending OTP emails
    and managing email verification workflow.
    """
    
    @staticmethod
    def send_verification_email(user):
        """
        Send OTP verification email to a user.
        
        Args:
            user: User instance to send verification email to
            
        Returns:
            tuple: (success: bool, verification: EmailVerification or None, error_message: str or None)
        """
        try:
            # Create new OTP verification
            verification = EmailVerification.create_for_user(user)
            
            # Email subject and context
            subject = f"Your DayLog verification code: {verification.otp_code}"
            context = {
                'user': user,
                'otp_code': verification.otp_code,
                'expires_in_minutes': 10,
                'site_name': 'DayLog',
            }
            
            # Render email templates
            html_content = render_to_string('authentication/emails/otp_verification.html', context)
            text_content = render_to_string('authentication/emails/otp_verification.txt', context)
            
            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            
            # Attach HTML version
            email.attach_alternative(html_content, "text/html")
            
            # Send email
            email.send()
            
            logger.info(f"OTP verification email sent successfully to {user.email}")
            return True, verification, None
            
        except Exception as e:
            logger.error(f"Failed to send OTP verification email to {user.email}: {str(e)}")
            return False, None, str(e)
    
    @staticmethod
    def verify_otp(user, otp_code):
        """
        Verify an OTP code for a user.
        
        Args:
            user: User instance
            otp_code: The OTP code to verify
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            verification = EmailVerification.get_valid_otp(user, otp_code)
            
            if not verification:
                return False, "Invalid or expired verification code"
            
            # Mark OTP as used and verify user's email
            verification.mark_as_used()
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
            
            logger.info(f"Email verification successful for user {user.username}")
            return True, None
            
        except Exception as e:
            logger.error(f"OTP verification failed for user {user.username}: {str(e)}")
            return False, "An error occurred during verification"
    
    @staticmethod
    def resend_verification_email(user):
        """
        Resend verification email to a user.
        
        This method invalidates any existing unused OTP codes and sends a new one.
        
        Args:
            user: User instance to resend verification email to
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            # Mark all existing unused OTPs as used
            EmailVerification.objects.filter(
                user=user, 
                is_used=False
            ).update(is_used=True)
            
            # Send new verification email
            success, verification, error = EmailVerificationService.send_verification_email(user)
            
            if success:
                logger.info(f"OTP verification email resent successfully to {user.email}")
                return True, None
            else:
                return False, error
                
        except Exception as e:
            logger.error(f"Failed to resend OTP verification email to {user.email}: {str(e)}")
            return False, "Failed to resend verification email"