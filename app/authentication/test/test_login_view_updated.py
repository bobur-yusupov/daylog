from typing import Dict, Any
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpResponse
from authentication.forms import CustomAuthenticationForm
from authentication.models import EmailVerification
from authentication.services import EmailVerificationService

User = get_user_model()


class UserLoginViewTests(TestCase):
    """
    Comprehensive test cases for user login view with email verification checks.
    """

    def setUp(self):
        self.client: Client = Client()
        self.login_url = reverse("authentication:login")
        self.verify_email_url = reverse("authentication:verify_email")
        self.home_url = "/"

        # Create verified test user
        self.verified_user: AbstractBaseUser = User.objects.create_user(
            username="verifieduser",
            email="verified@example.com",
            password="securepassword123",
            is_email_verified=True
        )
        
        # Create unverified test user
        self.unverified_user: AbstractBaseUser = User.objects.create_user(
            username="unverifieduser",
            email="unverified@example.com",
            password="securepassword123",
            is_email_verified=False
        )

    def test_get_login_view_success(self) -> None:
        """
        Test GET request to login view returns correct template and form.
        """
        response: HttpResponse = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200, "Response should be 200 OK")
        self.assertTemplateUsed(response, "authentication/login.html")
        self.assertContains(response, "form", msg_prefix="Response should contain form")
        self.assertIsInstance(
            response.context["form"],
            CustomAuthenticationForm,
            "Context should contain CustomAuthenticationForm",
        )

    def test_get_login_view_with_authenticated_user(self) -> None:
        """
        Test that authenticated users are redirected away from login page.
        """
        # Login as verified user
        self.client.force_login(self.verified_user)

        response: HttpResponse = self.client.get(self.login_url)
        
        # Should redirect authenticated users
        self.assertEqual(response.status_code, 302, "Should redirect authenticated users")

    def test_successful_login_verified_user(self) -> None:
        """
        Test successful login with verified email address.
        """
        login_data = {
            'username': 'verifieduser',
            'password': 'securepassword123'
        }
        
        response: HttpResponse = self.client.post(self.login_url, login_data)
        
        # Should redirect to home page
        self.assertRedirects(response, self.home_url)
        
        # User should be logged in
        user = self.client.session.get('_auth_user_id')
        self.assertEqual(user, str(self.verified_user.id))

    @patch.object(EmailVerificationService, 'send_verification_email')
    def test_login_attempt_unverified_user_with_email_success(self, mock_send_email) -> None:
        """
        Test login attempt by unverified user triggers email verification flow.
        """
        # Mock successful email sending
        from authentication.services.email_verification_service import EmailVerificationResult
        mock_verification = MagicMock()
        mock_send_email.return_value = EmailVerificationResult(success=True, verification=mock_verification)
        
        login_data = {
            'username': 'unverifieduser',
            'password': 'securepassword123'
        }
        
        response: HttpResponse = self.client.post(self.login_url, login_data)
        
        # Should redirect to email verification
        self.assertRedirects(response, self.verify_email_url)
        
        # User should NOT be logged in
        self.assertNotIn('_auth_user_id', self.client.session)
        
        # Session should contain pending verification user ID
        self.assertIn('pending_verification_user_id', self.client.session)
        self.assertEqual(
            self.client.session['pending_verification_user_id'],
            str(self.unverified_user.id)
        )
        
        # Email service should be called
        mock_send_email.assert_called_once_with(self.unverified_user)

    @patch.object(EmailVerificationService, 'send_verification_email')
    def test_login_attempt_unverified_user_email_failure(self, mock_send_email) -> None:
        """
        Test login attempt by unverified user when email sending fails.
        """
        # Mock email sending failure
        from authentication.services.email_verification_service import EmailVerificationResult
        mock_send_email.return_value = EmailVerificationResult(success=False, error_message="SMTP Error")
        
        login_data = {
            'username': 'unverifieduser',
            'password': 'securepassword123'
        }
        
        response: HttpResponse = self.client.post(self.login_url, login_data)
        
        # Should still redirect to email verification
        self.assertRedirects(response, self.verify_email_url)
        
        # User should NOT be logged in
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_invalid_credentials(self) -> None:
        """
        Test login with invalid credentials shows error message.
        """
        invalid_data = {
            'username': 'verifieduser',
            'password': 'wrongpassword'
        }
        
        response: HttpResponse = self.client.post(self.login_url, invalid_data)
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/login.html")
        
        # Should show error message
        messages = list(response.context['messages'])
        self.assertTrue(any('Invalid username or password' in str(m) for m in messages))
        
        # User should not be logged in
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_nonexistent_user(self) -> None:
        """
        Test login with nonexistent user shows error message.
        """
        invalid_data = {
            'username': 'nonexistentuser',
            'password': 'anypassword'
        }
        
        response: HttpResponse = self.client.post(self.login_url, invalid_data)
        
        # Should stay on login page with error
        self.assertEqual(response.status_code, 200)
        messages = list(response.context['messages'])
        self.assertTrue(any('Invalid username or password' in str(m) for m in messages))

    def test_login_with_next_parameter_verified_user(self) -> None:
        """
        Test login with 'next' parameter redirects verified user correctly.
        """
        next_url = reverse('authentication:profile')
        login_data = {
            'username': 'verifieduser',
            'password': 'securepassword123'
        }
        
        response: HttpResponse = self.client.post(f"{self.login_url}?next={next_url}", login_data)
        
        # Should redirect to 'next' URL
        self.assertRedirects(response, next_url)

    def test_login_empty_form_submission(self) -> None:
        """
        Test login with empty form shows validation errors.
        """
        response: HttpResponse = self.client.post(self.login_url, {})
        
        # Should stay on login page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/login.html")
        
        # Form should have errors
        form = response.context['form']
        self.assertTrue(form.errors)

    def test_login_csrf_protection(self) -> None:
        """
        Test that CSRF protection is enabled for login.
        """
        # Create client that enforces CSRF
        csrf_client = Client(enforce_csrf_checks=True)
        
        login_data = {
            'username': 'verifieduser',
            'password': 'securepassword123'
        }
        
        response: HttpResponse = csrf_client.post(self.login_url, login_data)
        
        # Should reject request without CSRF token
        self.assertEqual(response.status_code, 403)

    def test_login_case_sensitive_username(self) -> None:
        """
        Test that username is case sensitive (Django default behavior).
        """
        login_data = {
            'username': 'VERIFIEDUSER',  # Wrong case
            'password': 'securepassword123'
        }
        
        response: HttpResponse = self.client.post(self.login_url, login_data)
        
        # Should fail to login
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_multiple_failed_login_attempts(self) -> None:
        """
        Test multiple failed login attempts (basic test, no rate limiting implemented).
        """
        invalid_data = {
            'username': 'verifieduser',
            'password': 'wrongpassword'
        }
        
        # Multiple failed attempts
        for _ in range(3):
            response = self.client.post(self.login_url, invalid_data)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('_auth_user_id', self.client.session)
        
        # Should still allow attempts (no rate limiting implemented yet)
        valid_data = {
            'username': 'verifieduser',
            'password': 'securepassword123'
        }
        
        response = self.client.post(self.login_url, valid_data)
        self.assertRedirects(response, self.home_url)


class LoginIntegrationTests(TestCase):
    """
    Integration tests for login flow with email verification.
    """
    
    def setUp(self):
        self.client = Client()
        self.login_url = reverse("authentication:login")
        self.verify_email_url = reverse("authentication:verify_email")
        
        # Create unverified user with existing verification
        self.unverified_user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_email_verified=False
        )
        
        # Create existing verification record
        self.verification = EmailVerification.objects.create(
            user=self.unverified_user,
            otp_code="123456"
        )

    def test_login_unverified_user_creates_new_verification(self) -> None:
        """
        Test that login attempt by unverified user creates new verification record.
        """
        initial_verifications = EmailVerification.objects.filter(user=self.unverified_user).count()
        
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        # Attempt login
        response = self.client.post(self.login_url, login_data)
        
        # Should redirect to verification
        self.assertRedirects(response, self.verify_email_url)
        
        # Should have more verification records
        final_verifications = EmailVerification.objects.filter(user=self.unverified_user).count()
        self.assertGreater(final_verifications, initial_verifications)