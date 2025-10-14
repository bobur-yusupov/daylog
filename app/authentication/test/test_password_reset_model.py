from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from authentication.models import PasswordReset

User = get_user_model()


class PasswordResetModelTests(TestCase):
    """
    Unit tests for PasswordReset model methods and properties.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_password_reset_creation(self):
        """Test creating a password reset generates OTP and sets expiry."""
        password_reset = PasswordReset.objects.create(user=self.user)
        
        # Check OTP is generated
        self.assertIsNotNone(password_reset.otp_code)
        self.assertEqual(len(password_reset.otp_code), 6)
        self.assertTrue(password_reset.otp_code.isdigit())
        
        # Check expiry is set
        self.assertIsNotNone(password_reset.expires_at)
        expected_expiry = timezone.now() + timedelta(minutes=10)
        # Allow 1 second tolerance for test execution time
        self.assertAlmostEqual(
            password_reset.expires_at.timestamp(),
            expected_expiry.timestamp(),
            delta=1
        )
        
        # Check defaults
        self.assertFalse(password_reset.is_used)
        self.assertEqual(password_reset.attempts, 0)

    def test_generate_otp_format(self):
        """Test OTP generation creates valid 6-digit code."""
        otp = PasswordReset.generate_otp()
        
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())
        
        # Test multiple generations are different (very likely)
        otp2 = PasswordReset.generate_otp()
        self.assertNotEqual(otp, otp2)

    def test_create_for_user_invalidates_existing(self):
        """Test creating new password reset invalidates existing ones."""
        # Create first password reset
        first_reset = PasswordReset.objects.create(user=self.user)
        self.assertFalse(first_reset.is_used)
        
        # Create second password reset
        second_reset = PasswordReset.create_for_user(self.user)
        
        # First should be marked as used
        first_reset.refresh_from_db()
        self.assertTrue(first_reset.is_used)
        
        # Second should be active
        self.assertFalse(second_reset.is_used)
        self.assertNotEqual(first_reset.otp_code, second_reset.otp_code)

    def test_is_valid_fresh_password_reset(self):
        """Test fresh password reset is valid."""
        password_reset = PasswordReset.objects.create(user=self.user)
        self.assertTrue(password_reset.is_valid())

    def test_is_valid_used_password_reset(self):
        """Test used password reset is invalid."""
        password_reset = PasswordReset.objects.create(user=self.user)
        password_reset.is_used = True
        password_reset.save()
        
        self.assertFalse(password_reset.is_valid())

    def test_is_valid_expired_password_reset(self):
        """Test expired password reset is invalid."""
        password_reset = PasswordReset.objects.create(user=self.user)
        # Set expiry to past
        password_reset.expires_at = timezone.now() - timedelta(minutes=1)
        password_reset.save()
        
        self.assertFalse(password_reset.is_valid())

    def test_is_valid_max_attempts_reached(self):
        """Test password reset with max attempts is invalid."""
        password_reset = PasswordReset.objects.create(user=self.user)
        password_reset.attempts = 5  # Max attempts
        password_reset.save()
        
        self.assertFalse(password_reset.is_valid())

    def test_increment_attempts(self):
        """Test incrementing attempts works correctly."""
        password_reset = PasswordReset.objects.create(user=self.user)
        initial_attempts = password_reset.attempts
        
        password_reset.increment_attempts()
        
        self.assertEqual(password_reset.attempts, initial_attempts + 1)
        
        # Test multiple increments
        password_reset.increment_attempts()
        self.assertEqual(password_reset.attempts, initial_attempts + 2)

    def test_mark_as_used(self):
        """Test marking password reset as used."""
        password_reset = PasswordReset.objects.create(user=self.user)
        self.assertFalse(password_reset.is_used)
        
        password_reset.mark_as_used()
        
        self.assertTrue(password_reset.is_used)

    def test_str_representation(self):
        """Test string representation of password reset."""
        password_reset = PasswordReset.objects.create(user=self.user)
        expected = f"Password reset OTP for {self.user.email} - Valid"
        self.assertEqual(str(password_reset), expected)
        
        # Test invalid state
        password_reset.is_used = True
        password_reset.save()
        expected = f"Password reset OTP for {self.user.email} - Invalid"
        self.assertEqual(str(password_reset), expected)

    def test_meta_ordering(self):
        """Test password resets are ordered by creation time (newest first)."""
        first_reset = PasswordReset.objects.create(user=self.user)
        second_reset = PasswordReset.objects.create(user=self.user)
        
        resets = list(PasswordReset.objects.all())
        self.assertEqual(resets[0], second_reset)  # Newest first
        self.assertEqual(resets[1], first_reset)

    def test_custom_expiry_time(self):
        """Test setting custom expiry time."""
        custom_expiry = timezone.now() + timedelta(hours=1)
        password_reset = PasswordReset(user=self.user, expires_at=custom_expiry)
        password_reset.save()
        
        self.assertEqual(password_reset.expires_at, custom_expiry)

    def test_custom_otp_code(self):
        """Test setting custom OTP code."""
        custom_otp = "123456"
        password_reset = PasswordReset(user=self.user, otp_code=custom_otp)
        password_reset.save()
        
        self.assertEqual(password_reset.otp_code, custom_otp)