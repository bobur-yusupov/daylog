from typing import Dict, Any
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth import get_user_model
from django.core import mail
from authentication.forms import CustomUserCreationForm
from authentication.models import EmailVerification
from authentication.services import EmailVerificationService

User = get_user_model()


class UserRegistrationViewTests(TestCase):
    """
    Comprehensive test cases for user registration view with email verification.
    """

    def setUp(self):
        self.client: Client = Client()
        self.register_url = reverse("authentication:register")
        self.login_url = reverse("authentication:login")
        self.verify_email_url = reverse("authentication:verify_email")

        # Create an existing user for testing conflicts
        self.existing_user: AbstractBaseUser = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="securepassword123",
            is_email_verified=True  # Existing user is verified
        )

        self.valid_registration_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'honeypot': ''  # Empty honeypot field
        }

    def test_get_registration_view_success(self) -> None:
        """
        Test GET request to registration view returns correct template and form.
        """
        response: HttpResponse = self.client.get(self.register_url)

        self.assertEqual(response.status_code, 200, "Response should be 200 OK")
        self.assertTemplateUsed(response, "authentication/register.html")
        self.assertContains(response, "form", msg_prefix="Response should contain form")
        self.assertIsInstance(
            response.context["form"],
            CustomUserCreationForm,
            "Context should contain CustomUserCreationForm",
        )

    def test_get_registration_view_with_authenticated_user(self) -> None:
        """
        Test that authenticated users are redirected away from registration page.
        """
        # Login as existing user
        self.client.force_login(self.existing_user)

        response: HttpResponse = self.client.get(self.register_url)
        
        # Should redirect authenticated users
        self.assertEqual(response.status_code, 302, "Should redirect authenticated users")

    @patch.object(EmailVerificationService, 'send_verification_email')
    def test_successful_registration_with_email_verification(self, mock_send_email) -> None:
        """
        Test successful user registration triggers email verification process.
        """
        # Mock successful email sending
        mock_verification = MagicMock()
        from authentication.services.email_verification_service import EmailVerificationResult
        mock_send_email.return_value = EmailVerificationResult(success=True, verification=mock_verification)

        response: HttpResponse = self.client.post(self.register_url, self.valid_registration_data)
        
        # Should redirect to email verification page
        self.assertRedirects(response, self.verify_email_url)
        
        # User should be created but not email verified
        user = User.objects.get(username='newuser')
        self.assertIsNotNone(user)
        self.assertFalse(user.is_email_verified)
        self.assertEqual(user.email, 'newuser@example.com')
        
        # Session should contain user ID for verification
        session = self.client.session
        self.assertIn('pending_verification_user_id', session)
        self.assertEqual(session['pending_verification_user_id'], str(user.id))
        
        # Email service should be called
        mock_send_email.assert_called_once_with(user)

    @patch.object(EmailVerificationService, 'send_verification_email')
    def test_registration_with_email_sending_failure(self, mock_send_email) -> None:
        """
        Test registration when email sending fails still creates user.
        """
        # Mock email sending failure
        from authentication.services.email_verification_service import EmailVerificationResult
        mock_send_email.return_value = EmailVerificationResult(success=False, error_message="SMTP Error")

        response: HttpResponse = self.client.post(self.register_url, self.valid_registration_data)
        
        # Should still redirect to email verification page
        self.assertRedirects(response, self.verify_email_url)
        
        # User should still be created
        user = User.objects.get(username='newuser')
        self.assertIsNotNone(user)
        self.assertFalse(user.is_email_verified)

    def test_registration_with_invalid_data(self) -> None:
        """
        Test registration with invalid data shows form errors.
        """
        invalid_data = self.valid_registration_data.copy()
        invalid_data['password2'] = 'DifferentPassword123!'  # Mismatched passwords
        
        response: HttpResponse = self.client.post(self.register_url, invalid_data)
        
        # Should stay on registration page
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/register.html")
        
        # Should show form errors
        self.assertTrue(response.context['form'].errors)
        self.assertIn('password2', response.context['form'].errors)
        
        # User should not be created
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_registration_with_existing_username(self) -> None:
        """
        Test registration with existing username shows error.
        """
        invalid_data = self.valid_registration_data.copy()
        invalid_data['username'] = self.existing_user.username
        
        response: HttpResponse = self.client.post(self.register_url, invalid_data)
        
        # Should stay on registration page with error
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('username', response.context['form'].errors)

    def test_registration_with_existing_email(self) -> None:
        """
        Test registration with existing email shows error.
        """
        invalid_data = self.valid_registration_data.copy()
        invalid_data['email'] = self.existing_user.email
        
        response: HttpResponse = self.client.post(self.register_url, invalid_data)
        
        # Should stay on registration page with error
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('email', response.context['form'].errors)

    def test_registration_with_honeypot_spam_detection(self) -> None:
        """
        Test registration with filled honeypot field is detected as spam.
        """
        spam_data = self.valid_registration_data.copy()
        spam_data['honeypot'] = 'spam content'
        
        response: HttpResponse = self.client.post(self.register_url, spam_data)
        
        # Should stay on registration page
        self.assertEqual(response.status_code, 200)
        
        # User should not be created
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_registration_with_weak_password(self) -> None:
        """
        Test registration with weak password shows validation errors.
        """
        weak_password_data = self.valid_registration_data.copy()
        weak_password_data['password1'] = '123'
        weak_password_data['password2'] = '123'
        
        response: HttpResponse = self.client.post(self.register_url, weak_password_data)
        
        # Should stay on registration page with errors
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('password2', response.context['form'].errors)

    def test_registration_redirects_authenticated_users(self) -> None:
        """
        Test that authenticated users cannot access registration page.
        """
        self.client.force_login(self.existing_user)
        
        response: HttpResponse = self.client.post(self.register_url, self.valid_registration_data)
        
        # Should redirect away from registration
        self.assertEqual(response.status_code, 302)
        
        # New user should not be created
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_registration_csrf_protection(self) -> None:
        """
        Test that CSRF protection is enabled for registration.
        """
        # Create client that enforces CSRF
        csrf_client = Client(enforce_csrf_checks=True)
        
        response: HttpResponse = csrf_client.post(self.register_url, self.valid_registration_data)
        
        # Should reject request without CSRF token
        self.assertEqual(response.status_code, 403)

    @patch.object(EmailVerificationService, 'send_verification_email')
    def test_multiple_registrations_same_email_prevented(self, mock_send_email) -> None:
        """
        Test that multiple registrations with same email are prevented.
        """
        from authentication.services.email_verification_service import EmailVerificationResult
        mock_send_email.return_value = EmailVerificationResult(success=True, verification=MagicMock())
        
        # First registration
        response1 = self.client.post(self.register_url, self.valid_registration_data)
        self.assertRedirects(response1, self.verify_email_url)
        
        # Second registration with same email
        second_data = self.valid_registration_data.copy()
        second_data['username'] = 'anotheruser'
        
        response2 = self.client.post(self.register_url, second_data)
        
        # Should show error for duplicate email
        self.assertEqual(response2.status_code, 200)
        self.assertTrue(response2.context['form'].errors)
        self.assertIn('email', response2.context['form'].errors)


class UserRegistrationIntegrationTests(TestCase):
    """
    Integration tests for the complete registration flow.
    """

    def setUp(self):
        self.client = Client()
        self.register_url = reverse("authentication:register")
        self.verify_email_url = reverse("authentication:verify_email")
        
        self.valid_data = {
            'username': 'integrationuser',
            'email': 'integration@example.com',
            'first_name': 'Integration',
            'last_name': 'User',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'honeypot': ''
        }

    def test_full_registration_flow_integration(self) -> None:
        """
        Test complete registration flow from form submission to email verification.
        """
        # Clear any existing mail
        mail.outbox.clear()
        
        # Submit registration
        response = self.client.post(self.register_url, self.valid_data)
        
        # Should redirect to verification
        self.assertRedirects(response, self.verify_email_url)
        
        # User should exist and be unverified
        user = User.objects.get(username='integrationuser')
        self.assertFalse(user.is_email_verified)
        
        # EmailVerification record should be created
        verification = EmailVerification.objects.get(user=user)
        self.assertIsNotNone(verification)
        self.assertTrue(verification.is_valid())
        
        # Email should be sent (in test mode, check outbox)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn('verification code', email.subject.lower())
        self.assertEqual(email.to, [user.email])
        self.assertIn(verification.otp_code, email.body)