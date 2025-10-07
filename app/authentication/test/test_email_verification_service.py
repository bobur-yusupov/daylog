from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.template.loader import TemplateDoesNotExist
from django.core.mail import BadHeaderError
from unittest.mock import patch, MagicMock, Mock
from smtplib import SMTPException
from socket import gaierror

from authentication.models import EmailVerification
from authentication.services import EmailVerificationService
from authentication.services.email_verification_service import EmailVerificationResult
from authentication.exceptions import EmailDeliveryError, TemplateRenderingError

User = get_user_model()


class EmailVerificationServiceTests(TestCase):
    """
    Unit tests for EmailVerificationService methods and error handling.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_email_verified=False
        )

    def tearDown(self):
        """Clean up after each test."""
        mail.outbox.clear()

    def test_send_verification_email_success(self):
        """Test successful email verification sending."""
        result = EmailVerificationService.send_verification_email(self.user)
        
        # Should return success result
        self.assertIsInstance(result, EmailVerificationResult)
        self.assertTrue(result.success)
        self.assertIsNotNone(result.verification)
        self.assertIsNone(result.error_message)
        
        # Should create EmailVerification record
        verification = EmailVerification.objects.get(user=self.user)
        self.assertIsNotNone(verification)
        self.assertTrue(verification.is_valid())
        
        # Should send email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('verification code', email.subject.lower())
        self.assertEqual(email.to, [self.user.email])
        self.assertIn(verification.otp_code, email.body)

    def test_send_verification_email_creates_verification_record(self):
        """Test that sending email creates proper verification record."""
        initial_count = EmailVerification.objects.count()
        
        result = EmailVerificationService.send_verification_email(self.user)
        
        self.assertTrue(result.success)
        self.assertEqual(EmailVerification.objects.count(), initial_count + 1)
        
        verification = result.verification
        self.assertEqual(verification.user, self.user)
        self.assertEqual(len(verification.otp_code), 6)
        self.assertTrue(verification.otp_code.isdigit())

    @patch('authentication.services.email_verification_service.render_to_string')
    def test_send_verification_email_template_error(self, mock_render):
        """Test handling of template rendering errors."""
        mock_render.side_effect = TemplateDoesNotExist("Template not found")
        
        result = EmailVerificationService.send_verification_email(self.user)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.verification)
        self.assertIsNotNone(result.error_message)
        self.assertIn("template", result.error_message.lower())

    @patch('authentication.services.email_verification_service.EmailMultiAlternatives.send')
    def test_send_verification_email_smtp_error(self, mock_send):
        """Test handling of SMTP errors during email sending."""
        mock_send.side_effect = SMTPException("SMTP server error")
        
        result = EmailVerificationService.send_verification_email(self.user)
        
        self.assertFalse(result.success)
        self.assertIsNone(result.verification)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Failed to send verification email", result.error_message)

    @patch('authentication.services.email_verification_service.EmailMultiAlternatives.send')
    def test_send_verification_email_bad_header_error(self, mock_send):
        """Test handling of bad header errors during email sending."""
        mock_send.side_effect = BadHeaderError("Invalid header")
        
        result = EmailVerificationService.send_verification_email(self.user)
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)

    @patch('authentication.services.email_verification_service.EmailMultiAlternatives.send')
    def test_send_verification_email_network_error(self, mock_send):
        """Test handling of network errors during email sending."""
        mock_send.side_effect = gaierror("Network unreachable")
        
        result = EmailVerificationService.send_verification_email(self.user)
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)

    def test_verify_otp_success(self):
        """Test successful OTP verification."""
        verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="123456"
        )
        
        result = EmailVerificationService.verify_email_with_otp(self.user, "123456")
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        
        # User should be verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        
        # Verification should be marked as used
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)

    def test_verify_otp_invalid_code(self):
        """Test OTP verification with invalid code."""
        EmailVerification.objects.create(
            user=self.user,
            otp_code="123456"
        )
        
        result = EmailVerificationService.verify_email_with_otp(self.user, "999999")
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)
        self.assertIn("Invalid or expired", result.error_message)
        
        # User should remain unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_verify_otp_expired_code(self):
        """Test OTP verification with expired code."""
        from django.utils import timezone
        from datetime import timedelta
        
        past_time = timezone.now() - timedelta(minutes=1)
        verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="123456",
            expires_at=past_time
        )
        
        result = EmailVerificationService.verify_email_with_otp(self.user, "123456")
        
        self.assertFalse(result.success)
        self.assertIn("Invalid or expired", result.error_message)

    def test_verify_otp_used_code(self):
        """Test OTP verification with already used code."""
        verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="123456",
            is_used=True
        )
        
        result = EmailVerificationService.verify_email_with_otp(self.user, "123456")
        
        self.assertFalse(result.success)
        self.assertIn("Invalid or expired", result.error_message)

    def test_verify_otp_no_verification_record(self):
        """Test OTP verification when no verification record exists."""
        result = EmailVerificationService.verify_email_with_otp(self.user, "123456")
        
        self.assertFalse(result.success)
        self.assertIn("Invalid or expired", result.error_message)

    @patch.object(User, 'save')
    def test_verify_otp_database_error(self, mock_save):
        """Test OTP verification with database error during save."""
        from django.db import DatabaseError
        
        verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="123456"
        )
        
        mock_save.side_effect = DatabaseError("Database connection failed")
        
        result = EmailVerificationService.verify_email_with_otp(self.user, "123456")
        
        self.assertFalse(result.success)
        self.assertIn("Database error", result.error_message)

    def test_resend_verification_email_success(self):
        """Test successful resending of verification email."""
        # Create existing verification
        old_verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="111111"
        )
        
        result = EmailVerificationService.resend_verification_email(self.user)
        
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)
        
        # Old verification should be marked as used
        old_verification.refresh_from_db()
        self.assertTrue(old_verification.is_used)
        
        # New verification should be created
        new_verifications = EmailVerification.objects.filter(
            user=self.user, 
            is_used=False
        )
        self.assertEqual(new_verifications.count(), 1)
        
        # Email should be sent
        self.assertEqual(len(mail.outbox), 1)

    def test_resend_verification_email_multiple_existing(self):
        """Test resending email when multiple verifications exist."""
        # Create multiple existing verifications
        verification1 = EmailVerification.objects.create(
            user=self.user,
            otp_code="111111"
        )
        verification2 = EmailVerification.objects.create(
            user=self.user,
            otp_code="222222"
        )
        
        result = EmailVerificationService.resend_verification_email(self.user)
        
        self.assertTrue(result.success)
        
        # All old verifications should be marked as used
        verification1.refresh_from_db()
        verification2.refresh_from_db()
        self.assertTrue(verification1.is_used)
        self.assertTrue(verification2.is_used)
        
        # Only one new verification should exist
        new_verifications = EmailVerification.objects.filter(
            user=self.user, 
            is_used=False
        )
        self.assertEqual(new_verifications.count(), 1)

    @patch.object(EmailVerificationService, 'send_verification_email')
    def test_resend_verification_email_sending_failure(self, mock_send):
        """Test resend when email sending fails."""
        mock_send.return_value = EmailVerificationResult(
            success=False, 
            error_message="Email sending failed"
        )
        
        result = EmailVerificationService.resend_verification_email(self.user)
        
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error_message)

    def test_email_template_context(self):
        """Test that email templates receive correct context variables."""
        EmailVerificationService.send_verification_email(self.user)
        
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        # Check that context variables are in the email body
        self.assertIn(self.user.email, email.to)
        self.assertIn('DayLog', email.body)  # Site name
        
        # Check that OTP is in the email
        verification = EmailVerification.objects.get(user=self.user)
        self.assertIn(verification.otp_code, email.body)

    @override_settings(DEFAULT_FROM_EMAIL='test@daylog.com')
    def test_email_from_address(self):
        """Test that email is sent from correct address."""
        EmailVerificationService.send_verification_email(self.user)
        
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.from_email, 'test@daylog.com')

    def test_email_subject_contains_otp(self):
        """Test that email subject contains the OTP code."""
        EmailVerificationService.send_verification_email(self.user)
        
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        verification = EmailVerification.objects.get(user=self.user)
        self.assertIn(verification.otp_code, email.subject)

    def test_email_has_html_alternative(self):
        """Test that email includes HTML alternative."""
        EmailVerificationService.send_verification_email(self.user)
        
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        # Check that HTML alternative is attached
        self.assertTrue(hasattr(email, 'alternatives'))
        html_alternatives = [alt for alt in email.alternatives if alt[1] == 'text/html']
        self.assertEqual(len(html_alternatives), 1)

    def test_service_constants(self):
        """Test that service class constants are set correctly."""
        self.assertEqual(
            EmailVerificationService.OTP_TEMPLATE_HTML,
            'authentication/emails/otp_verification.html'
        )
        self.assertEqual(
            EmailVerificationService.OTP_TEMPLATE_TEXT,
            'authentication/emails/otp_verification.txt'
        )
        self.assertEqual(EmailVerificationService.SITE_NAME, 'DayLog')
        self.assertIsInstance(EmailVerificationService.OTP_EXPIRY_MINUTES, int)

    def test_concurrent_verification_creation(self):
        """Test service behavior with multiple verification creation (simulated concurrency)."""
        # Instead of actual threading (which causes SQLite issues), 
        # test multiple sequential calls to verify the service handles multiple verifications
        results = []
        
        # Create multiple verifications sequentially to avoid SQLite locking
        for i in range(3):
            result = EmailVerificationService.send_verification_email(self.user)
            results.append(result)
        
        # All should succeed
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.success for r in results))
        
        # Should have created 3 verification records
        verifications = EmailVerification.objects.filter(user=self.user)
        self.assertEqual(verifications.count(), 3)
        
        # All should be valid
        for verification in verifications:
            self.assertTrue(verification.is_valid())
