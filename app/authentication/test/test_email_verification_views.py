from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from unittest.mock import patch
import json

from authentication.models import EmailVerification
from authentication.services import EmailVerificationService
from authentication.forms import OTPVerificationForm, ResendOTPForm

User = get_user_model()


class EmailVerificationViewTests(TestCase):
    """
    Integration tests for EmailVerificationView and related functionality.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.client = Client()
        self.verify_email_url = reverse("authentication:verify_email")
        self.register_url = reverse("authentication:register")
        self.login_url = reverse("authentication:login")

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_email_verified=False,
        )

        self.verification = EmailVerification.objects.create(
            user=self.user, otp_code="123456"
        )

    def test_get_verify_email_view_without_session(self):
        """Test accessing verification view without pending session redirects to register."""
        response = self.client.get(self.verify_email_url)

        self.assertRedirects(response, self.register_url)

        # Should show error message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("No pending verification" in str(m) for m in messages))

    def test_get_verify_email_view_with_valid_session(self):
        """Test accessing verification view with valid session shows form."""
        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        response = self.client.get(self.verify_email_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/email_verification.html")
        self.assertIsInstance(response.context["form"], OTPVerificationForm)
        self.assertIsInstance(response.context["resend_form"], ResendOTPForm)
        self.assertEqual(response.context["user"], self.user)

    def test_verify_email_view_context_data(self):
        """Test that verification view provides correct context data."""
        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        response = self.client.get(self.verify_email_url)

        self.assertIn("masked_email", response.context)
        masked_email = response.context["masked_email"]

        # Should mask email properly (t***@example.com)
        self.assertIn("@example.com", masked_email)
        self.assertIn("*", masked_email)
        self.assertTrue(masked_email.startswith("t"))

    def test_verify_email_view_with_nonexistent_user(self):
        """Test verification view with invalid user ID in session."""
        # Set up session with valid UUID format but nonexistent user
        import uuid

        nonexistent_uuid = str(uuid.uuid4())

        session = self.client.session
        session["pending_verification_user_id"] = nonexistent_uuid
        session.save()

        response = self.client.get(self.verify_email_url)

        self.assertRedirects(response, self.register_url)

    def test_verify_email_view_with_verified_user(self):
        """Test verification view with already verified user."""
        # Mark user as verified
        self.user.is_email_verified = True
        self.user.save()

        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        response = self.client.get(self.verify_email_url)

        self.assertRedirects(response, self.register_url)

    def test_post_verify_email_success(self):
        """Test successful email verification via POST."""
        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        form_data = {"otp_code": "123456"}
        response = self.client.post(self.verify_email_url, form_data)

        self.assertRedirects(response, self.login_url)

        # User should be verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

        # Verification should be used
        self.verification.refresh_from_db()
        self.assertTrue(self.verification.is_used)

        # Session should be cleared
        session = self.client.session
        self.assertNotIn("pending_verification_user_id", session)

    def test_post_verify_email_invalid_code(self):
        """Test email verification with invalid OTP code."""
        # Create a verification first
        EmailVerification.objects.create(user=self.user)

        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        form_data = {
            "otp_code": "999999"
        }  # Wrong code, verification has different code
        response = self.client.post(self.verify_email_url, form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/email_verification.html")

        # User should remain unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

        # Should show error message (Django messages or form errors)
        messages = list(response.context["messages"])
        if messages:
            message_texts = [str(m) for m in messages]
            # If there are messages, one should be about invalid verification
            has_error_message = any(
                "Invalid" in text or "check" in text for text in message_texts
            )
        else:
            # If no messages, check if form has errors (alternative error display)
            form = response.context.get("form")
            has_error_message = form and not form.is_valid()

        self.assertTrue(
            has_error_message,
            "Should have error message or form errors for invalid OTP",
        )

    def test_post_verify_email_form_validation_errors(self):
        """Test email verification with form validation errors."""
        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        form_data = {"otp_code": "12345"}  # Too short
        response = self.client.post(self.verify_email_url, form_data)

        self.assertEqual(response.status_code, 200)
        # Check form errors in context
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertIn("otp_code", form.errors)
        # Django's default validation message for min_length
        self.assertIn(
            "Ensure this value has at least 6 characters", str(form.errors["otp_code"])
        )

    def test_verify_email_csrf_protection(self):
        """Test that CSRF protection is enabled for verification."""
        # Create client that enforces CSRF
        csrf_client = Client(enforce_csrf_checks=True)

        # Set up session on csrf_client
        session = csrf_client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        form_data = {"otp_code": "123456"}
        response = csrf_client.post(self.verify_email_url, form_data)

        # Should reject request without CSRF token
        self.assertEqual(response.status_code, 403)


class ResendOTPViewTests(TestCase):
    """
    Integration tests for ResendOTPView functionality.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.client = Client()
        self.resend_otp_url = reverse("authentication:resend_otp")
        self.verify_email_url = reverse("authentication:verify_email")

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_email_verified=False,
        )

    def test_get_resend_otp_redirects(self):
        """Test that GET request to resend OTP redirects to verification page."""
        # Set up session so verification page doesn't redirect
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        response = self.client.get(self.resend_otp_url)

        self.assertRedirects(response, self.verify_email_url)

    @patch.object(EmailVerificationService, "resend_verification_email")
    def test_post_resend_otp_success(self, mock_resend):
        """Test successful OTP resend via POST."""
        # Mock successful resend
        from authentication.services.email_verification_service import (
            EmailVerificationResult,
        )

        mock_resend.return_value = EmailVerificationResult(success=True)

        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        response = self.client.post(self.resend_otp_url)

        self.assertEqual(response.status_code, 200)

        # Should return JSON response
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertIn("verification code has been sent", data["message"])

        # Service should be called
        mock_resend.assert_called_once_with(self.user)

    @patch.object(EmailVerificationService, "resend_verification_email")
    def test_post_resend_otp_failure(self, mock_resend):
        """Test OTP resend failure via POST."""
        # Mock resend failure
        from authentication.services.email_verification_service import (
            EmailVerificationResult,
        )

        mock_resend.return_value = EmailVerificationResult(
            success=False, error_message="Email sending failed"
        )

        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        response = self.client.post(self.resend_otp_url)

        self.assertEqual(response.status_code, 500)

        # Should return JSON error response
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("Email sending failed", data["message"])

    def test_post_resend_otp_no_session(self):
        """Test OTP resend without valid session."""
        response = self.client.post(self.resend_otp_url)

        self.assertEqual(response.status_code, 400)

        # Should return JSON error response
        data = json.loads(response.content)
        self.assertFalse(data["success"])
        self.assertIn("No pending verification", data["message"])

    def test_post_resend_otp_invalid_user(self):
        """Test OTP resend with invalid user ID in session."""
        # Set up session with invalid user ID
        import uuid

        session = self.client.session
        session["pending_verification_user_id"] = str(uuid.uuid4())
        session.save()

        response = self.client.post(self.resend_otp_url)

        self.assertEqual(response.status_code, 400)

        # Should return JSON error response
        data = json.loads(response.content)
        self.assertFalse(data["success"])

    def test_resend_otp_csrf_protection(self):
        """Test that CSRF protection is enabled for OTP resend."""
        # Create client that enforces CSRF
        csrf_client = Client(enforce_csrf_checks=True)

        # Set up session on csrf_client
        session = csrf_client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        response = csrf_client.post(self.resend_otp_url)

        # Should reject request without CSRF token
        self.assertEqual(response.status_code, 403)


class SkipVerificationViewTests(TestCase):
    """
    Integration tests for SkipVerificationView (development only).
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.client = Client()
        self.skip_verification_url = reverse("authentication:skip_verification")
        self.register_url = reverse("authentication:register")
        self.login_url = reverse("authentication:login")

        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_email_verified=False,
        )

    def test_skip_verification_success(self):
        """Test successful verification skip (development only)."""
        # Set up session
        session = self.client.session
        session["pending_verification_user_id"] = str(self.user.id)
        session.save()

        response = self.client.post(self.skip_verification_url)

        self.assertRedirects(response, self.login_url)

        # User should be verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

        # Session should be cleared
        session = self.client.session
        self.assertNotIn("pending_verification_user_id", session)

    def test_skip_verification_no_session(self):
        """Test verification skip without valid session."""
        response = self.client.post(self.skip_verification_url)

        self.assertRedirects(response, self.register_url)

    def test_skip_verification_invalid_user(self):
        """Test verification skip with invalid user ID."""
        # Set up session with invalid user ID
        import uuid

        session = self.client.session
        session["pending_verification_user_id"] = str(uuid.uuid4())
        session.save()

        response = self.client.post(self.skip_verification_url)

        self.assertRedirects(response, self.register_url)


class EmailVerificationFlowIntegrationTests(TestCase):
    """
    Integration tests for the complete email verification flow.
    """

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.register_url = reverse("authentication:register")
        self.verify_email_url = reverse("authentication:verify_email")
        self.resend_otp_url = reverse("authentication:resend_otp")
        self.login_url = reverse("authentication:login")

        self.registration_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "SecurePassword123!",
            "password2": "SecurePassword123!",
            "honeypot": "",
        }

    def test_complete_registration_verification_flow(self):
        """Test complete flow from registration to email verification."""
        # Clear mail outbox
        mail.outbox.clear()

        # Step 1: Register user
        response = self.client.post(self.register_url, self.registration_data)
        self.assertRedirects(response, self.verify_email_url)

        # User should be created but not verified
        user = User.objects.get(username="newuser")
        self.assertFalse(user.is_email_verified)

        # Session should contain user ID
        session = self.client.session
        self.assertIn("pending_verification_user_id", session)

        # Email should be sent
        self.assertEqual(len(mail.outbox), 1)

        # Step 2: Access verification page
        response = self.client.get(self.verify_email_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "verification code")

        # Step 3: Submit correct OTP
        verification = EmailVerification.objects.get(user=user)
        form_data = {"otp_code": verification.otp_code}
        response = self.client.post(self.verify_email_url, form_data)

        self.assertRedirects(response, self.login_url)

        # User should now be verified
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

        # Session should be cleared
        session = self.client.session
        self.assertNotIn("pending_verification_user_id", session)

    def test_registration_with_resend_otp(self):
        """Test registration flow with OTP resend functionality."""
        # Register user
        response = self.client.post(self.register_url, self.registration_data)
        self.assertRedirects(response, self.verify_email_url)

        user = User.objects.get(username="newuser")
        initial_verification = EmailVerification.objects.get(user=user)

        # Resend OTP
        response = self.client.post(self.resend_otp_url)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertTrue(data["success"])

        # Should have new verification record
        new_verifications = EmailVerification.objects.filter(user=user, is_used=False)
        self.assertEqual(new_verifications.count(), 1)

        # Old verification should be marked as used
        initial_verification.refresh_from_db()
        self.assertTrue(initial_verification.is_used)

    def test_multiple_verification_attempts(self):
        """Test multiple verification attempts with same code."""
        # Register and get verification code
        self.client.post(self.register_url, self.registration_data)
        user = User.objects.get(username="newuser")
        verification = EmailVerification.objects.get(user=user)

        # First verification attempt (should succeed)
        form_data = {"otp_code": verification.otp_code}
        response = self.client.post(self.verify_email_url, form_data)
        self.assertRedirects(response, self.login_url)

        # User should be verified
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

        # Create new session for second attempt
        new_user = User.objects.create_user(
            username="anotheruser",
            email="another@example.com",
            password="testpass123",
            is_email_verified=False,
        )
        EmailVerification.objects.create(
            user=new_user, otp_code=verification.otp_code  # Same code
        )

        session = self.client.session
        session["pending_verification_user_id"] = str(new_user.id)
        session.save()

        # Second attempt with same code (should succeed for different user)
        response = self.client.post(self.verify_email_url, form_data)
        self.assertRedirects(response, self.login_url)

    def test_session_persistence_across_requests(self):
        """Test that session data persists correctly across requests."""
        # Register user
        self.client.post(self.register_url, self.registration_data)

        # Check session after registration
        session = self.client.session
        user_id = session.get("pending_verification_user_id")
        self.assertIsNotNone(user_id)

        # Make multiple requests to verification page
        for _ in range(3):
            response = self.client.get(self.verify_email_url)
            self.assertEqual(response.status_code, 200)

            # Session should persist
            session = self.client.session
            self.assertEqual(session.get("pending_verification_user_id"), user_id)

        # Verify OTP to clear session
        user = User.objects.get(id=user_id)
        verification = EmailVerification.objects.get(user=user)
        form_data = {"otp_code": verification.otp_code}

        self.client.post(self.verify_email_url, form_data)

        # Session should now be cleared
        session = self.client.session
        self.assertNotIn("pending_verification_user_id", session)
