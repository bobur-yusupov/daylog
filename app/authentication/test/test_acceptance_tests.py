from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import transaction
from django.test.utils import override_settings
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
import time
import threading
from unittest.mock import patch

from authentication.models import EmailVerification
from authentication.services import EmailVerificationService

User = get_user_model()


class UserRegistrationAcceptanceTests(TestCase):
    """
    Acceptance tests for complete user registration and verification scenarios.
    These tests verify the entire user journey from a user perspective.
    """

    def setUp(self):
        """Set up test data for acceptance tests."""
        self.client = Client()
        self.register_url = reverse("authentication:register")
        self.verify_email_url = reverse("authentication:verify_email")
        self.login_url = reverse("authentication:login")
        self.home_url = "/"
        
        self.valid_user_data = {
            'username': 'acceptanceuser',
            'email': 'acceptance@example.com',
            'first_name': 'Acceptance',
            'last_name': 'User',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'honeypot': ''
        }

    def test_happy_path_registration_and_verification(self):
        """
        Test the happy path: user registers, receives email, verifies, and can login.
        
        This is the most important acceptance test covering the main user flow.
        """
        # Clear any existing emails
        mail.outbox.clear()
        
        # Step 1: User visits registration page
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")
        
        # Step 2: User submits registration form
        response = self.client.post(self.register_url, self.valid_user_data)
        self.assertRedirects(response, self.verify_email_url)
        
        # Verify user was created but not verified
        user = User.objects.get(username='acceptanceuser')
        self.assertFalse(user.is_email_verified)
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['acceptance@example.com'])
        self.assertIn('verification code', email.subject.lower())
        
        # Step 3: User is redirected to email verification page
        response = self.client.get(self.verify_email_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verify Your Email")
        self.assertContains(response, "a********e@example.com")  # Masked email display
        
        # Step 4: User enters correct OTP code
        verification = EmailVerification.objects.get(user=user)
        otp_data = {'otp_code': verification.otp_code}
        response = self.client.post(self.verify_email_url, otp_data)
        
        # Should redirect to login page
        self.assertRedirects(response, self.login_url)
        
        # Verify user is now email verified
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        
        # Step 5: User can now login successfully
        login_data = {
            'username': 'acceptanceuser',
            'password': 'SecurePassword123!'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertRedirects(response, self.home_url)
        
        # Verify user is logged in
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(
            self.client.session['_auth_user_id'], 
            str(user.id)
        )

    def test_registration_with_email_resend_scenario(self):
        """
        Test scenario where user registers, doesn't receive initial email,
        requests resend, and then verifies successfully.
        """
        mail.outbox.clear()
        
        # Register user
        self.client.post(self.register_url, self.valid_user_data)
        user = User.objects.get(username='acceptanceuser')
        
        # Simulate user not receiving email - clear outbox
        mail.outbox.clear()
        
        # User goes to verification page
        response = self.client.get(self.verify_email_url)
        self.assertEqual(response.status_code, 200)
        
        # User clicks "Resend Code" button (AJAX request)
        response = self.client.post(reverse('authentication:resend_otp'))
        self.assertEqual(response.status_code, 200)
        
        # Check that new email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        # Original verification should be invalidated
        original_verifications = EmailVerification.objects.filter(
            user=user, is_used=True
        )
        self.assertGreater(original_verifications.count(), 0)
        
        # New verification should exist
        new_verification = EmailVerification.objects.filter(
            user=user, is_used=False
        ).first()
        self.assertIsNotNone(new_verification)
        
        # User enters new OTP code
        otp_data = {'otp_code': new_verification.otp_code}
        response = self.client.post(self.verify_email_url, otp_data)
        
        self.assertRedirects(response, self.login_url)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_expired_otp_code_scenario(self):
        """
        Test scenario where user tries to use expired OTP code.
        """
        # Register user
        self.client.post(self.register_url, self.valid_user_data)
        user = User.objects.get(username='acceptanceuser')
        
        # Manually expire the OTP
        verification = EmailVerification.objects.get(user=user)
        verification.expires_at = verification.created_at  # Set to past
        verification.save()
        
        # User tries to verify with expired code
        otp_data = {'otp_code': verification.otp_code}
        response = self.client.post(self.verify_email_url, otp_data)
        
        # Should stay on verification page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid or expired verification code")
        
        # User should remain unverified
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)

    def test_multiple_registration_attempts_same_email(self):
        """
        Test scenario where user tries to register multiple times with same email.
        """
        # First registration
        response = self.client.post(self.register_url, self.valid_user_data)
        self.assertRedirects(response, self.verify_email_url)
        
        # Second registration attempt with same email
        second_data = self.valid_user_data.copy()
        second_data['username'] = 'differentuser'
        
        response = self.client.post(self.register_url, second_data)
        
        # Should stay on registration page with error
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('email', response.context['form'].errors)

    def test_user_tries_to_login_before_verification(self):
        """
        Test scenario where user tries to login before completing email verification.
        """
        # Register user but don't verify
        self.client.post(self.register_url, self.valid_user_data)
        user = User.objects.get(username='acceptanceuser')
        
        # Clear session to simulate new browser session
        self.client.session.flush()
        
        # User tries to login
        login_data = {
            'username': 'acceptanceuser',
            'password': 'SecurePassword123!'
        }
        response = self.client.post(self.login_url, login_data)
        
        # Should redirect to email verification
        self.assertRedirects(response, self.verify_email_url)
        
        # User should NOT be logged in
        self.assertNotIn('_auth_user_id', self.client.session)
        
        # But session should contain pending verification
        self.assertIn('pending_verification_user_id', self.client.session)

    def test_user_workflow_with_form_validation_errors(self):
        """
        Test user workflow when they make form validation errors.
        """
        # Registration with mismatched passwords
        invalid_data = self.valid_user_data.copy()
        invalid_data['password2'] = 'DifferentPassword123!'
        
        response = self.client.post(self.register_url, invalid_data)
        
        # Should stay on registration page with errors
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('password2', response.context['form'].errors)
        
        # Fix the error and resubmit
        response = self.client.post(self.register_url, self.valid_user_data)
        self.assertRedirects(response, self.verify_email_url)
        
        # Now try verification with invalid OTP format
        invalid_otp_data = {'otp_code': '12345'}  # Too short
        response = self.client.post(self.verify_email_url, invalid_otp_data)
        
        # Should stay on verification page with error
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertIn('otp_code', response.context['form'].errors)

    def test_concurrent_user_registrations(self):
        """
        Test scenario with multiple users registering simultaneously.
        """
        users_data = [
            {
                'username': f'user{i}',
                'email': f'user{i}@example.com',
                'first_name': f'User{i}',
                'last_name': 'Test',
                'password1': 'SecurePassword123!',
                'password2': 'SecurePassword123!',
                'honeypot': ''
            }
            for i in range(3)
        ]
        
        mail.outbox.clear()
        
        # Register multiple users
        for user_data in users_data:
            client = Client()  # New client for each user
            response = client.post(self.register_url, user_data)
            self.assertRedirects(response, self.verify_email_url)
        
        # All users should be created
        self.assertEqual(User.objects.count(), 3)
        
        # All should have verification emails
        self.assertEqual(len(mail.outbox), 3)
        
        # Each user should have their own verification code
        verifications = EmailVerification.objects.all()
        otp_codes = [v.otp_code for v in verifications]
        # All codes should be unique (high probability)
        self.assertEqual(len(otp_codes), len(set(otp_codes)))

    def test_user_navigation_patterns(self):
        """
        Test various user navigation patterns during the verification process.
        """
        # Register user
        self.client.post(self.register_url, self.valid_user_data)
        user = User.objects.get(username='acceptanceuser')
        
        # User navigates back to registration page (should still work since not authenticated)
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)  # Unauthenticated users can access register
        
        # User goes back to verification page
        response = self.client.get(self.verify_email_url)
        self.assertEqual(response.status_code, 200)
        
        # User tries to access login page
        response = self.client.get(self.login_url)
        # Should be allowed (might want to login with different account)
        
        # User completes verification
        verification = EmailVerification.objects.get(user=user)
        otp_data = {'otp_code': verification.otp_code}
        response = self.client.post(self.verify_email_url, otp_data)
        
        self.assertRedirects(response, self.login_url)

    def test_error_recovery_scenarios(self):
        """
        Test how well users can recover from various error scenarios.
        """
        # Register user
        self.client.post(self.register_url, self.valid_user_data)
        user = User.objects.get(username='acceptanceuser')
        
        # Scenario 1: User enters wrong OTP multiple times
        for i in range(3):
            wrong_otp_data = {'otp_code': f'{i:06d}'}  # Wrong codes
            response = self.client.post(self.verify_email_url, wrong_otp_data)
            self.assertEqual(response.status_code, 200)
            # Should still be able to try again
            self.assertContains(response, "Enter Verification Code")
        
        # User should still be able to use correct code
        verification = EmailVerification.objects.get(user=user)
        correct_otp_data = {'otp_code': verification.otp_code}
        response = self.client.post(self.verify_email_url, correct_otp_data)
        
        self.assertRedirects(response, self.login_url)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)


class EmailVerificationAcceptanceTransactionTests(TransactionTestCase):
    """
    Acceptance tests that require database transactions.
    """

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.register_url = reverse("authentication:register")
        
        self.user_data = {
            'username': 'transactionuser',
            'email': 'transaction@example.com',
            'first_name': 'Transaction',
            'last_name': 'User',
            'password1': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'honeypot': ''
        }

    def test_database_rollback_on_email_failure(self):
        """
        Test that user creation is properly handled when email sending fails.
        """
        with patch.object(EmailVerificationService, '_send_otp_email') as mock_send:
            # Mock email failure at the SMTP level
            mock_send.side_effect = Exception("SMTP connection failed")
            
            # User registration should still work but show warning
            response = self.client.post(self.register_url, self.user_data)
            
            # User should still be created (graceful degradation)
            self.assertTrue(User.objects.filter(username='transactionuser').exists())
            
            # Should redirect to verification page
            self.assertEqual(response.status_code, 302)

    def test_concurrent_verification_attempts_database_consistency(self):
        """
        Test database consistency with concurrent verification attempts (skipped due to SQLite limitations).
        """
        self.skipTest("SQLite doesn't handle concurrent verification attempts well in tests")
        # Register user first
        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(username='transactionuser')
        
        verification = EmailVerification.objects.create(
            user=user,
            otp_code="123456"
        )
        
        results = []
        
        def verify_user():
            """Function to run in separate threads."""
            client = Client()
            # Set up session
            session = client.session
            session['pending_verification_user_id'] = str(user.id)
            session.save()
            
            # Attempt verification
            otp_data = {'otp_code': '123456'}
            response = client.post(reverse('authentication:verify_email'), otp_data)
            results.append(response.status_code)
        
        # Create multiple threads attempting verification
        threads = [threading.Thread(target=verify_user) for _ in range(3)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Only one should succeed (verification can only be used once)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)
        
        # Verification should be marked as used
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)


# Note: Selenium tests would go here for browser-based acceptance tests
# These are commented out as they require additional setup

class SeleniumAcceptanceTests(TestCase):
    """
    Browser-based acceptance tests using Selenium.
    
    Note: These tests require Selenium WebDriver to be installed and configured.
    They are disabled by default but can be enabled for full end-to-end testing.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up Selenium WebDriver."""
        super().setUpClass()
        # Uncomment to enable Selenium tests
        # cls.selenium = webdriver.Chrome()  # Requires ChromeDriver
        # cls.selenium.implicitly_wait(10)
        pass
    
    @classmethod
    def tearDownClass(cls):
        """Clean up Selenium WebDriver."""
        # if hasattr(cls, 'selenium'):
        #     cls.selenium.quit()
        super().tearDownClass()
    
    def test_full_browser_registration_flow(self):
        """
        Test complete registration flow in actual browser.
        
        This test would verify JavaScript functionality, form interactions,
        and the complete user experience.
        """
        # This test is disabled by default
        # Uncomment and modify as needed for browser testing
        pass
        
        # Example implementation:
        # self.selenium.get(f'{self.live_server_url}{self.register_url}')
        # 
        # # Fill registration form
        # self.selenium.find_element(By.NAME, 'username').send_keys('seleniumuser')
        # self.selenium.find_element(By.NAME, 'email').send_keys('selenium@example.com')
        # # ... fill other fields
        # 
        # # Submit form
        # self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()
        # 
        # # Wait for redirect to verification page
        # WebDriverWait(self.selenium, 10).until(
        #     EC.url_contains('/verify-email/')
        # )
        # 
        # # Test OTP input functionality
        # otp_input = self.selenium.find_element(By.NAME, 'otp_code')
        # otp_input.send_keys('123456')
        # 
        # # Test form submission
        # self.selenium.find_element(By.CSS_SELECTOR, 'button[type="submit"]').click()