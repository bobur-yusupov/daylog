from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.template.loader import TemplateDoesNotExist
from django.utils import timezone
from unittest.mock import patch, Mock
from smtplib import SMTPException

from authentication.models import PasswordReset
from authentication.services import PasswordResetService
from authentication.services.password_reset_service import PasswordResetResult

User = get_user_model()


class PasswordResetServiceTests(TestCase):
    """
    Unit tests for PasswordResetService methods and error handling.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.inactive_user = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="testpass123",
            is_active=False,
        )

    def test_send_password_reset_otp_success(self):
        """Test successful OTP email sending."""
        result = PasswordResetService.send_password_reset_otp(self.user)

        self.assertTrue(result.success)
        self.assertIsInstance(result.password_reset, PasswordReset)
        self.assertIsNone(result.error_message)

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, [self.user.email])
        self.assertIn("Password Reset Code", email.subject)
        self.assertIn(result.password_reset.otp_code, email.body)

    def test_send_password_reset_otp_creates_model(self):
        """Test that sending OTP creates PasswordReset model."""
        initial_count = PasswordReset.objects.count()

        result = PasswordResetService.send_password_reset_otp(self.user)

        self.assertEqual(PasswordReset.objects.count(), initial_count + 1)
        password_reset = PasswordReset.objects.get(user=self.user)
        self.assertEqual(result.password_reset, password_reset)

    @patch("authentication.services.password_reset_service.render_to_string")
    def test_send_password_reset_otp_template_error(self, mock_render):
        """Test handling of template rendering errors."""
        mock_render.side_effect = TemplateDoesNotExist("template not found")

        result = PasswordResetService.send_password_reset_otp(self.user)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to render email template", result.error_message)

    @patch("authentication.services.password_reset_service.EmailMultiAlternatives.send")
    def test_send_password_reset_otp_smtp_error(self, mock_send):
        """Test handling of SMTP errors."""
        mock_send.side_effect = SMTPException("SMTP server error")

        result = PasswordResetService.send_password_reset_otp(self.user)

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to send email", result.error_message)

    def test_get_user_by_email_existing_active_user(self):
        """Test getting an existing active user by email."""
        user = PasswordResetService.get_user_by_email(self.user.email)
        self.assertEqual(user, self.user)

    def test_get_user_by_email_inactive_user(self):
        """Test getting inactive user returns None."""
        user = PasswordResetService.get_user_by_email(self.inactive_user.email)
        self.assertIsNone(user)

    def test_get_user_by_email_nonexistent_user(self):
        """Test getting nonexistent user returns None."""
        user = PasswordResetService.get_user_by_email("nonexistent@example.com")
        self.assertIsNone(user)

    def test_get_user_by_email_case_sensitivity(self):
        """Test email lookup is case sensitive (as expected)."""
        user = PasswordResetService.get_user_by_email("TEST@EXAMPLE.COM")
        self.assertIsNone(user)  # Should be None due to case sensitivity

    def test_verify_otp_valid_code(self):
        """Test verifying valid OTP code."""
        password_reset = PasswordReset.create_for_user(self.user)

        result = PasswordResetService.verify_otp(
            self.user.email, password_reset.otp_code
        )

        self.assertEqual(result, password_reset)
        # Check that attempts were incremented
        password_reset.refresh_from_db()
        self.assertEqual(password_reset.attempts, 1)

    def test_verify_otp_invalid_code(self):
        """Test verifying invalid OTP code."""
        PasswordReset.create_for_user(self.user)

        result = PasswordResetService.verify_otp(self.user.email, "999999")

        self.assertIsNone(result)

    def test_verify_otp_expired_code(self):
        """Test verifying expired OTP code."""
        password_reset = PasswordReset.create_for_user(self.user)
        # Expire the OTP
        password_reset.expires_at = timezone.now() - timezone.timedelta(minutes=1)
        password_reset.save()

        result = PasswordResetService.verify_otp(
            self.user.email, password_reset.otp_code
        )

        self.assertIsNone(result)

    def test_verify_otp_used_code(self):
        """Test verifying already used OTP code."""
        password_reset = PasswordReset.create_for_user(self.user)
        password_reset.mark_as_used()

        result = PasswordResetService.verify_otp(
            self.user.email, password_reset.otp_code
        )

        self.assertIsNone(result)

    def test_verify_otp_max_attempts_reached(self):
        """Test verifying OTP after max attempts reached."""
        password_reset = PasswordReset.create_for_user(self.user)
        password_reset.attempts = 4  # One less than max
        password_reset.save()

        # This should fail (attempts becomes 5, which equals max, so is_valid returns False)
        result = PasswordResetService.verify_otp(
            self.user.email, password_reset.otp_code
        )
        self.assertIsNone(result)

        # Verify attempts was incremented
        password_reset.refresh_from_db()
        self.assertEqual(password_reset.attempts, 5)

    def test_verify_otp_nonexistent_user(self):
        """Test verifying OTP for nonexistent user."""
        result = PasswordResetService.verify_otp("nonexistent@example.com", "123456")
        self.assertIsNone(result)

    def test_verify_otp_no_password_reset(self):
        """Test verifying OTP when no password reset exists."""
        result = PasswordResetService.verify_otp(self.user.email, "123456")
        self.assertIsNone(result)

    def test_reset_password_with_otp_success(self):
        """Test successful password reset with OTP."""
        password_reset = PasswordReset.create_for_user(self.user)
        new_password = "newpassword123"

        success = PasswordResetService.reset_password_with_otp(
            self.user.email, password_reset.otp_code, new_password
        )

        self.assertTrue(success)

        # Check password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        # Check OTP was marked as used
        password_reset.refresh_from_db()
        self.assertTrue(password_reset.is_used)

    @override_settings(PASSWORD_RESET_CONFIRMATION_EMAIL_ENABLED=True)
    def test_reset_password_with_otp_sends_confirmation_email(self):
        """Test that password reset sends confirmation email."""
        password_reset = PasswordReset.create_for_user(self.user)

        # Clear any existing emails
        mail.outbox = []

        success = PasswordResetService.reset_password_with_otp(
            self.user.email, password_reset.otp_code, "newpassword123"
        )

        self.assertTrue(success)
        # Should have 2 emails: OTP email + confirmation email
        self.assertEqual(
            len(mail.outbox), 1
        )  # Only confirmation (OTP was sent during create_for_user)

    @override_settings(PASSWORD_RESET_CONFIRMATION_EMAIL_ENABLED=False)
    def test_reset_password_with_otp_no_confirmation_email_when_disabled(self):
        """Test that password reset doesn't send confirmation email when disabled."""
        password_reset = PasswordReset.create_for_user(self.user)
        initial_email_count = len(mail.outbox)

        success = PasswordResetService.reset_password_with_otp(
            self.user.email, password_reset.otp_code, "newpassword123"
        )

        self.assertTrue(success)
        # Should not have additional emails beyond the OTP email
        self.assertEqual(len(mail.outbox), initial_email_count)

    def test_reset_password_with_otp_invalid_code(self):
        """Test password reset with invalid OTP code."""
        PasswordReset.create_for_user(self.user)

        success = PasswordResetService.reset_password_with_otp(
            self.user.email, "999999", "newpassword123"
        )

        self.assertFalse(success)

    def test_can_resend_otp_no_previous_reset(self):
        """Test can resend OTP when no previous reset exists."""
        can_resend = PasswordResetService.can_resend_otp(self.user)
        self.assertTrue(can_resend)

    def test_can_resend_otp_after_interval(self):
        """Test can resend OTP after interval has passed."""
        password_reset = PasswordReset.create_for_user(self.user)
        # Set creation time to past the resend interval
        password_reset.created_at = timezone.now() - timezone.timedelta(seconds=61)
        password_reset.save()

        can_resend = PasswordResetService.can_resend_otp(self.user)
        self.assertTrue(can_resend)

    def test_cannot_resend_otp_within_interval(self):
        """Test cannot resend OTP within the interval."""
        PasswordReset.create_for_user(self.user)

        can_resend = PasswordResetService.can_resend_otp(self.user)
        self.assertFalse(can_resend)

    @patch("authentication.services.password_reset_service.EmailMultiAlternatives")
    def test_send_security_alert_email(self, mock_email):
        """Test sending security alert email."""
        mock_msg = Mock()
        mock_email.return_value = mock_msg

        PasswordResetService.send_security_alert_email(self.user, "suspicious_activity")

        # Check email was created and sent
        mock_email.assert_called_once()
        mock_msg.send.assert_called_once()

        # Check email content
        call_args = mock_email.call_args
        self.assertIn("Security Alert", call_args[1]["subject"])
        self.assertEqual(call_args[1]["to"], [self.user.email])

    @patch("authentication.services.password_reset_service.EmailMultiAlternatives.send")
    def test_send_security_alert_email_error_handling(self, mock_send):
        """Test security alert email error handling."""
        mock_send.side_effect = SMTPException("SMTP error")

        # Should not raise exception
        PasswordResetService.send_security_alert_email(self.user)

    def test_password_reset_result_dataclass(self):
        """Test PasswordResetResult dataclass."""
        # Test success result
        password_reset = PasswordReset.create_for_user(self.user)
        result = PasswordResetResult(success=True, password_reset=password_reset)

        self.assertTrue(result.success)
        self.assertEqual(result.password_reset, password_reset)
        self.assertIsNone(result.error_message)

        # Test error result
        error_result = PasswordResetResult(success=False, error_message="Test error")

        self.assertFalse(error_result.success)
        self.assertIsNone(error_result.password_reset)
        self.assertEqual(error_result.error_message, "Test error")
