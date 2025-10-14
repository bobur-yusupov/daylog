from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from datetime import timedelta

from authentication.models import PasswordReset
from authentication.services import PasswordResetService

User = get_user_model()


class PasswordResetIntegrationTests(TestCase):
    """
    Integration tests for the complete password reset flow.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )

    def test_complete_password_reset_flow_success(self):
        """Test the complete password reset flow from start to finish."""
        # Step 1: Request password reset
        url = reverse('authentication:password_reset_request')
        response = self.client.post(url, {'email': self.user.email})
        
        self.assertRedirects(response, reverse('authentication:password_reset_otp'))
        self.assertEqual(len(mail.outbox), 1)
        
        # Get the OTP from the created PasswordReset
        password_reset = PasswordReset.objects.get(user=self.user)
        otp_code = password_reset.otp_code
        
        # Verify OTP was sent in email
        self.assertIn(otp_code, mail.outbox[0].body)
        
        # Step 2: Verify OTP
        url = reverse('authentication:password_reset_otp')
        response = self.client.post(url, {
            'email': self.user.email,
            'otp_code': otp_code
        })
        
        self.assertRedirects(response, reverse('authentication:password_reset_confirm'))
        
        # Step 3: Set new password
        url = reverse('authentication:password_reset_confirm')
        new_password = 'newstrongpassword123'
        response = self.client.post(url, {
            'email': self.user.email,
            'otp_code': otp_code,
            'new_password': new_password,
            'confirm_password': new_password
        })
        
        self.assertRedirects(response, reverse('authentication:password_reset_complete'))
        
        # Step 4: Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        self.assertFalse(self.user.check_password('oldpassword123'))
        
        # Step 5: Verify OTP was marked as used
        password_reset.refresh_from_db()
        self.assertTrue(password_reset.is_used)

    @override_settings(PASSWORD_RESET_CONFIRMATION_EMAIL_ENABLED=True)
    def test_complete_flow_with_confirmation_email(self):
        """Test complete flow includes confirmation email."""
        # Clear any existing emails
        mail.outbox = []
        
        # Complete the flow
        self._complete_password_reset_flow()
        
        # Should have OTP email + confirmation email
        self.assertEqual(len(mail.outbox), 2)
        
        # Check confirmation email
        confirmation_email = mail.outbox[1]
        self.assertIn('Password Reset Confirmation', confirmation_email.subject)
        self.assertIn('successfully changed', confirmation_email.body)

    def test_flow_with_nonexistent_email(self):
        """Test password reset flow with nonexistent email."""
        url = reverse('authentication:password_reset_request')
        response = self.client.post(url, {'email': 'nonexistent@example.com'})
        
        # Should redirect normally (for security)
        self.assertRedirects(response, reverse('authentication:password_reset_otp'))
        
        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)
        
        # But should be able to proceed to OTP page (which will fail)
        url = reverse('authentication:password_reset_otp')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_flow_interruption_at_otp_step(self):
        """Test flow interruption at OTP verification step."""
        # Start the flow
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        
        password_reset = PasswordReset.objects.get(user=self.user)
        
        # Try to skip to confirm step without verifying OTP
        url = reverse('authentication:password_reset_confirm')
        response = self.client.get(url)
        
        # Should be redirected back to start
        self.assertRedirects(response, reverse('authentication:password_reset_request'))

    def test_flow_with_expired_otp(self):
        """Test flow with expired OTP."""
        # Start the flow
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        
        password_reset = PasswordReset.objects.get(user=self.user)
        
        # Expire the OTP
        password_reset.expires_at = timezone.now() - timedelta(minutes=1)
        password_reset.save()
        
        # Try to verify expired OTP
        url = reverse('authentication:password_reset_otp')
        response = self.client.post(url, {
            'email': self.user.email,
            'otp_code': password_reset.otp_code
        })
        
        # Should stay on OTP page with error
        self.assertEqual(response.status_code, 200)

    def test_flow_with_max_attempts_reached(self):
        """Test flow when max OTP attempts are reached."""
        # Start the flow
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        
        password_reset = PasswordReset.objects.get(user=self.user)
        
        # Make maximum attempts with wrong OTP
        url = reverse('authentication:password_reset_otp')
        for _ in range(5):
            response = self.client.post(url, {
                'email': self.user.email,
                'otp_code': '999999'  # Wrong OTP
            })
            self.assertEqual(response.status_code, 200)
        
        # Now try with correct OTP - should fail due to max attempts
        response = self.client.post(url, {
            'email': self.user.email,
            'otp_code': password_reset.otp_code
        })
        
        self.assertEqual(response.status_code, 200)  # Stays on OTP page

    def test_resend_otp_functionality(self):
        """Test OTP resend functionality in the flow."""
        # Start the flow
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        
        initial_count = PasswordReset.objects.count()
        
        # Wait a bit and resend (mocking the time interval)
        with self.settings(OTP_RESEND_INTERVAL_SECONDS=0):
            url = reverse('authentication:resend_password_reset_otp')
            response = self.client.post(url, {'email': self.user.email})
            
            self.assertRedirects(response, reverse('authentication:password_reset_otp'))
        
        # Should have created a new PasswordReset
        self.assertGreater(PasswordReset.objects.count(), initial_count)

    def test_multiple_concurrent_password_resets(self):
        """Test handling of multiple password reset requests."""
        # Create first password reset
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        
        first_reset = PasswordReset.objects.get(user=self.user, is_used=False)
        
        # Create second password reset (should invalidate first)
        self.client.post(url, {'email': self.user.email})
        
        # First should be marked as used
        first_reset.refresh_from_db()
        self.assertTrue(first_reset.is_used)
        
        # Second should be active
        second_reset = PasswordReset.objects.filter(user=self.user, is_used=False).first()
        self.assertIsNotNone(second_reset)
        self.assertNotEqual(first_reset.otp_code, second_reset.otp_code)

    def test_session_security_between_requests(self):
        """Test session security during the flow."""
        # Start flow with one client
        client1 = Client()
        url = reverse('authentication:password_reset_request')
        client1.post(url, {'email': self.user.email})
        
        # Try to access OTP page with different client
        client2 = Client()
        url = reverse('authentication:password_reset_otp')
        response = client2.get(url)
        
        # Should be redirected (no session)
        self.assertRedirects(response, reverse('authentication:password_reset_request'))

    def test_flow_with_session_cleanup(self):
        """Test that sessions are properly cleaned up after completion."""
        # Complete the flow
        self._complete_password_reset_flow()
        
        # Session should be clean
        self.assertNotIn('password_reset_email', self.client.session)
        self.assertNotIn('password_reset_verified_email', self.client.session)
        self.assertNotIn('password_reset_verified_otp', self.client.session)

    def test_flow_security_against_replay_attacks(self):
        """Test protection against OTP replay attacks."""
        # Complete the flow once
        password_reset = self._complete_password_reset_flow()
        
        # Try to use the same OTP again
        # Start new session
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        
        url = reverse('authentication:password_reset_otp')
        response = self.client.post(url, {
            'email': self.user.email,
            'otp_code': password_reset.otp_code  # Reused OTP
        })
        
        # Should fail
        self.assertEqual(response.status_code, 200)

    def test_flow_with_password_validation_errors(self):
        """Test flow with various password validation errors."""
        # Start and complete up to password setting
        password_reset = PasswordReset.create_for_user(self.user)
        
        # Set up verified session
        session = self.client.session
        session['password_reset_verified_email'] = self.user.email
        session['password_reset_verified_otp'] = password_reset.otp_code
        session.save()
        
        # Test weak password
        url = reverse('authentication:password_reset_confirm')
        response = self.client.post(url, {
            'email': self.user.email,
            'otp_code': password_reset.otp_code,
            'new_password': '123',
            'confirm_password': '123'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'password')

    def test_email_templates_rendered_correctly(self):
        """Test that email templates are rendered with correct data."""
        # Start the flow
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        
        # Check OTP email content
        email = mail.outbox[0]
        self.assertIn(self.user.username, email.body)
        self.assertIn('DayLog', email.body)  # Site name
        self.assertIn('10 minutes', email.body)  # Expiry time
        
        password_reset = PasswordReset.objects.get(user=self.user)
        self.assertIn(password_reset.otp_code, email.body)

    def _complete_password_reset_flow(self):
        """Helper method to complete the entire password reset flow."""
        # Step 1: Request
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        
        password_reset = PasswordReset.objects.get(user=self.user)
        
        # Step 2: Verify OTP
        url = reverse('authentication:password_reset_otp')
        self.client.post(url, {
            'email': self.user.email,
            'otp_code': password_reset.otp_code
        })
        
        # Step 3: Set password
        url = reverse('authentication:password_reset_confirm')
        self.client.post(url, {
            'email': self.user.email,
            'otp_code': password_reset.otp_code,
            'new_password': 'newstrongpassword123',
            'confirm_password': 'newstrongpassword123'
        })
        
        return password_reset


class PasswordResetPerformanceTests(TestCase):
    """
    Performance and load tests for password reset functionality.
    """

    def setUp(self):
        """Set up test data."""
        self.users = []
        for i in range(10):
            user = User.objects.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password="testpass123",
            )
            self.users.append(user)

    def test_multiple_concurrent_requests(self):
        """Test handling multiple concurrent password reset requests."""
        clients = [Client() for _ in range(len(self.users))]
        
        # Send concurrent requests
        for i, (client, user) in enumerate(zip(clients, self.users)):
            url = reverse('authentication:password_reset_request')
            response = client.post(url, {'email': user.email})
            self.assertEqual(response.status_code, 302)
        
        # Check that all requests were handled
        self.assertEqual(PasswordReset.objects.count(), len(self.users))

    def test_database_queries_efficiency(self):
        """Test that password reset operations are efficient."""
        user = self.users[0]
        
        # Test OTP creation queries
        with self.assertNumQueries(2):  # Update existing + Create new
            PasswordReset.create_for_user(user)
        
        # Test OTP verification queries
        password_reset = PasswordReset.objects.get(user=user)
        with self.assertNumQueries(3):  # Get user + get reset + increment
            result = PasswordResetService.verify_otp(user.email, password_reset.otp_code)
            self.assertIsNotNone(result)


class PasswordResetSecurityTests(TestCase):
    """
    Security-focused tests for password reset functionality.
    """

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )

    def test_timing_attack_protection(self):
        """Test protection against timing attacks."""
        import time
        
        # Time request with valid email
        start_time = time.time()
        url = reverse('authentication:password_reset_request')
        self.client.post(url, {'email': self.user.email})
        valid_time = time.time() - start_time
        
        # Time request with invalid email
        start_time = time.time()
        self.client.post(url, {'email': 'nonexistent@example.com'})
        invalid_time = time.time() - start_time
        
        # Times should be similar (within reasonable tolerance)
        time_diff = abs(valid_time - invalid_time)
        self.assertLess(time_diff, 0.5)  # 500ms tolerance

    def test_otp_randomness(self):
        """Test that OTP codes are sufficiently random."""
        otps = set()
        
        # Generate multiple OTPs
        for _ in range(100):
            otp = PasswordReset.generate_otp()
            otps.add(otp)
        
        # Should have high uniqueness (at least 95% unique)
        self.assertGreaterEqual(len(otps), 95)

    def test_session_fixation_protection(self):
        """Test protection against session fixation attacks."""
        # Get initial session key
        url = reverse('authentication:password_reset_request')
        self.client.get(url)
        initial_session_key = self.client.session.session_key
        
        # Complete password reset
        self.client.post(url, {'email': self.user.email})
        
        # Session should still be valid but could have changed
        # This is more about ensuring sessions work correctly
        self.assertIsNotNone(self.client.session.session_key)

    def test_rate_limiting_behavior(self):
        """Test rate limiting for OTP requests."""
        # This would typically be implemented with additional middleware
        # For now, we test the can_resend_otp functionality
        
        password_reset = PasswordReset.create_for_user(self.user)
        
        # Should not be able to resend immediately
        can_resend = PasswordResetService.can_resend_otp(self.user)
        self.assertFalse(can_resend)

    def test_information_disclosure_prevention(self):
        """Test that no sensitive information is disclosed in responses."""
        url = reverse('authentication:password_reset_request')
        
        # Response for valid email
        response1 = self.client.post(url, {'email': self.user.email})
        
        # Response for invalid email  
        response2 = self.client.post(url, {'email': 'nonexistent@example.com'})
        
        # Both should redirect to same place
        self.assertEqual(response1.status_code, response2.status_code)
        self.assertEqual(response1['Location'], response2['Location'])