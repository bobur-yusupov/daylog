from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core import mail
from unittest.mock import patch, Mock

from authentication.models import PasswordReset

User = get_user_model()


class PasswordResetViewsTests(TestCase):
    """
    Unit tests for password reset views.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )
        self.inactive_user = User.objects.create_user(
            username="inactive",
            email="inactive@example.com",
            password="testpass123",
            is_active=False,
        )

    # PasswordResetRequestView Tests
    def test_password_reset_request_get(self):
        """Test GET request to password reset request page."""
        url = reverse("authentication:password_reset_request")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reset Password")
        self.assertContains(response, "Enter your email to receive a verification code")

    def test_password_reset_request_post_valid_user(self):
        """Test POST request with valid user email."""
        url = reverse("authentication:password_reset_request")
        data = {"email": self.user.email}

        response = self.client.post(url, data)

        # Should redirect to OTP page
        self.assertRedirects(response, reverse("authentication:password_reset_otp"))

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

        # Check session data
        self.assertEqual(self.client.session["password_reset_email"], self.user.email)

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("6-digit verification code", str(messages[0]))

    def test_password_reset_request_post_invalid_user(self):
        """Test POST request with nonexistent user email."""
        url = reverse("authentication:password_reset_request")
        data = {"email": "nonexistent@example.com"}

        response = self.client.post(url, data)

        # Should still redirect (for security)
        self.assertRedirects(response, reverse("authentication:password_reset_otp"))

        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)

        # But session should still be set
        self.assertEqual(
            self.client.session["password_reset_email"], "nonexistent@example.com"
        )

    def test_password_reset_request_post_inactive_user(self):
        """Test POST request with inactive user email."""
        url = reverse("authentication:password_reset_request")
        data = {"email": self.inactive_user.email}

        response = self.client.post(url, data)

        # Should redirect but no email sent
        self.assertRedirects(response, reverse("authentication:password_reset_otp"))
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_request_post_invalid_form(self):
        """Test POST request with invalid form data."""
        url = reverse("authentication:password_reset_request")
        data = {"email": "invalid-email"}

        response = self.client.post(url, data)

        # Should stay on same page with errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enter a valid email address")

    @patch("authentication.services.PasswordResetService.send_password_reset_otp")
    def test_password_reset_request_service_failure(self, mock_send_otp):
        """Test handling of service failure during OTP send."""
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Service error"
        mock_send_otp.return_value = mock_result

        url = reverse("authentication:password_reset_request")
        data = {"email": self.user.email}

        response = self.client.post(url, data)

        # Should stay on same page with error
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("error" in str(msg).lower() for msg in messages))

    # PasswordResetOTPView Tests
    def test_password_reset_otp_get_with_session(self):
        """Test GET request to OTP page with valid session."""
        # Set up session
        session = self.client.session
        session["password_reset_email"] = self.user.email
        session.save()

        url = reverse("authentication:password_reset_otp")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verify Your Code")
        self.assertContains(response, self.user.email)

    def test_password_reset_otp_get_without_session(self):
        """Test GET request to OTP page without session."""
        url = reverse("authentication:password_reset_otp")
        response = self.client.get(url)

        # Should redirect to start
        self.assertRedirects(response, reverse("authentication:password_reset_request"))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("start the password reset process" in str(msg) for msg in messages)
        )

    def test_password_reset_otp_post_valid_code(self):
        """Test POST request with valid OTP code."""
        # Create password reset
        password_reset = PasswordReset.create_for_user(self.user)

        # Set up session
        session = self.client.session
        session["password_reset_email"] = self.user.email
        session.save()

        url = reverse("authentication:password_reset_otp")
        data = {"email": self.user.email, "otp_code": password_reset.otp_code}

        response = self.client.post(url, data)

        # Should redirect to confirm page
        self.assertRedirects(response, reverse("authentication:password_reset_confirm"))

        # Check verified session data
        self.assertEqual(
            self.client.session["password_reset_verified_email"], self.user.email
        )
        self.assertEqual(
            self.client.session["password_reset_verified_otp"], password_reset.otp_code
        )

    def test_password_reset_otp_post_invalid_code(self):
        """Test POST request with invalid OTP code."""
        PasswordReset.create_for_user(self.user)

        # Set up session
        session = self.client.session
        session["password_reset_email"] = self.user.email
        session.save()

        url = reverse("authentication:password_reset_otp")
        data = {"email": self.user.email, "otp_code": "999999"}

        response = self.client.post(url, data)

        # Should stay on same page with error
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid or expired" in str(msg) for msg in messages))

    # PasswordResetConfirmView Tests
    def test_password_reset_confirm_get_with_verified_session(self):
        """Test GET request to confirm page with verified session."""
        password_reset = PasswordReset.create_for_user(self.user)

        # Set up verified session
        session = self.client.session
        session["password_reset_verified_email"] = self.user.email
        session["password_reset_verified_otp"] = password_reset.otp_code
        session.save()

        url = reverse("authentication:password_reset_confirm")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Set New Password")
        self.assertContains(response, self.user.email)

    def test_password_reset_confirm_get_without_verified_session(self):
        """Test GET request to confirm page without verified session."""
        url = reverse("authentication:password_reset_confirm")
        response = self.client.get(url)

        # Should redirect to start
        self.assertRedirects(response, reverse("authentication:password_reset_request"))

    def test_password_reset_confirm_post_success(self):
        """Test POST request with valid password reset."""
        password_reset = PasswordReset.create_for_user(self.user)

        # Set up verified session
        session = self.client.session
        session["password_reset_verified_email"] = self.user.email
        session["password_reset_verified_otp"] = password_reset.otp_code
        session.save()

        url = reverse("authentication:password_reset_confirm")
        data = {
            "email": self.user.email,
            "otp_code": password_reset.otp_code,
            "new_password": "newstrongpassword123",
            "confirm_password": "newstrongpassword123",
        }

        response = self.client.post(url, data)

        # Should redirect to complete page
        self.assertRedirects(
            response, reverse("authentication:password_reset_complete")
        )

        # Check password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newstrongpassword123"))

        # Check session was cleared
        self.assertNotIn("password_reset_email", self.client.session)
        self.assertNotIn("password_reset_verified_email", self.client.session)
        self.assertNotIn("password_reset_verified_otp", self.client.session)

    def test_password_reset_confirm_post_password_mismatch(self):
        """Test POST request with password mismatch."""
        password_reset = PasswordReset.create_for_user(self.user)

        # Set up verified session
        session = self.client.session
        session["password_reset_verified_email"] = self.user.email
        session["password_reset_verified_otp"] = password_reset.otp_code
        session.save()

        url = reverse("authentication:password_reset_confirm")
        data = {
            "email": self.user.email,
            "otp_code": password_reset.otp_code,
            "new_password": "newstrongpassword123",
            "confirm_password": "differentpassword123",
        }

        response = self.client.post(url, data)

        # Should stay on same page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password fields must match")

    @patch("authentication.services.PasswordResetService.reset_password_with_otp")
    def test_password_reset_confirm_service_failure(self, mock_reset):
        """Test handling of service failure during password reset."""
        mock_reset.return_value = False

        password_reset = PasswordReset.create_for_user(self.user)

        # Set up verified session
        session = self.client.session
        session["password_reset_verified_email"] = self.user.email
        session["password_reset_verified_otp"] = password_reset.otp_code
        session.save()

        url = reverse("authentication:password_reset_confirm")
        data = {
            "email": self.user.email,
            "otp_code": password_reset.otp_code,
            "new_password": "newstrongpassword123",
            "confirm_password": "newstrongpassword123",
        }

        response = self.client.post(url, data)

        # Should redirect to start with error
        self.assertRedirects(response, reverse("authentication:password_reset_request"))

    # PasswordResetCompleteView Tests
    def test_password_reset_complete_get(self):
        """Test GET request to complete page."""
        url = reverse("authentication:password_reset_complete")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Password Reset Successful")
        self.assertContains(response, "confirmation email")

    # ResendPasswordResetOTPView Tests
    def test_resend_otp_post_with_session(self):
        """Test POST request to resend OTP with valid session."""
        # Set up session
        session = self.client.session
        session["password_reset_email"] = self.user.email
        session.save()

        url = reverse("authentication:resend_password_reset_otp")
        data = {"email": self.user.email}

        response = self.client.post(url, data)

        # Should redirect back to OTP page
        self.assertRedirects(response, reverse("authentication:password_reset_otp"))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("new verification code" in str(msg) for msg in messages))

    def test_resend_otp_post_without_session(self):
        """Test POST request to resend OTP without session."""
        url = reverse("authentication:resend_password_reset_otp")
        data = {"email": self.user.email}

        response = self.client.post(url, data)

        # Should redirect to start
        self.assertRedirects(response, reverse("authentication:password_reset_request"))

    @patch("authentication.services.PasswordResetService.can_resend_otp")
    def test_resend_otp_rate_limited(self, mock_can_resend):
        """Test resend OTP when rate limited."""
        mock_can_resend.return_value = False

        # Set up session
        session = self.client.session
        session["password_reset_email"] = self.user.email
        session.save()

        url = reverse("authentication:resend_password_reset_otp")
        data = {"email": self.user.email}

        response = self.client.post(url, data)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("wait before requesting" in str(msg) for msg in messages))

    # Anonymous Required Tests
    def test_authenticated_user_redirected(self):
        """Test that authenticated users are redirected away."""
        self.client.force_login(self.user)

        # Test the request view which should definitely redirect authenticated users
        url = reverse("authentication:password_reset_request")
        response = self.client.get(url, follow=False)

        # Should be redirected (302) and not show the form
        self.assertEqual(response.status_code, 302)

        # Test that we can't access the form when logged in
        response_with_follow = self.client.get(url, follow=True)
        # If properly redirected, we shouldn't see the password reset form
        self.assertNotContains(
            response_with_follow,
            "Enter your email to reset your password",
            status_code=200,
        )

    # Security Tests
    def test_session_isolation(self):
        """Test that sessions are properly isolated between users."""
        # First user starts password reset
        session1 = self.client.session
        session1["password_reset_email"] = self.user.email
        session1.save()

        # Create new client for second user
        client2 = Client()
        url = reverse("authentication:password_reset_otp")
        response = client2.get(url)

        # Second client should not have access
        self.assertRedirects(response, reverse("authentication:password_reset_request"))

    def test_expired_session_handling(self):
        """Test handling of sessions without proper flow completion."""
        # Skip to confirm page without going through OTP verification
        url = reverse("authentication:password_reset_confirm")
        response = self.client.get(url)

        # Should be redirected to start
        self.assertRedirects(response, reverse("authentication:password_reset_request"))

    def test_form_data_validation_in_views(self):
        """Test that views properly validate form data."""
        # Set up session state for OTP view
        session = self.client.session
        session["password_reset_email"] = self.user.email
        session.save()

        # Test invalid OTP format
        url = reverse("authentication:password_reset_otp")
        data = {"email": self.user.email, "otp_code": "invalid"}  # Not 6 digits

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)  # Stays on page
        # Check for validation error message
        self.assertContains(response, "Ensure this value has at most 6 characters")

    def test_csrf_protection(self):
        """Test CSRF protection on forms."""
        # Test that CSRF token is present in forms
        url = reverse("authentication:password_reset_request")
        response = self.client.get(url)

        # Check that CSRF token is in the form
        self.assertContains(response, "csrfmiddlewaretoken")

        # Test that forms require CSRF token
        # Create a new client to avoid CSRF tokens from GET request
        from django.test import Client

        new_client = Client(enforce_csrf_checks=True)
        data = {"email": self.user.email}
        response = new_client.post(url, data)

        # Should fail due to missing CSRF token
        self.assertEqual(response.status_code, 403)
