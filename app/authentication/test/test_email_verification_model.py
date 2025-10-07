from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import string

from authentication.models import EmailVerification

User = get_user_model()


class EmailVerificationModelTests(TestCase):
    """
    Unit tests for EmailVerification model methods and validation.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

    def test_email_verification_creation(self):
        """Test basic EmailVerification model creation."""
        verification = EmailVerification.objects.create(user=self.user)

        self.assertEqual(verification.user, self.user)
        self.assertTrue(verification.otp_code)
        self.assertEqual(len(verification.otp_code), 6)
        self.assertTrue(verification.otp_code.isdigit())
        self.assertFalse(verification.is_used)
        self.assertIsNotNone(verification.created_at)
        self.assertIsNotNone(verification.expires_at)

    def test_otp_code_generation(self):
        """Test OTP code generation produces valid 6-digit codes."""
        otp_code = EmailVerification.generate_otp()

        self.assertEqual(len(otp_code), 6)
        self.assertTrue(otp_code.isdigit())
        self.assertTrue(all(c in string.digits for c in otp_code))

    def test_otp_code_uniqueness(self):
        """Test that generated OTP codes are reasonably unique."""
        # Generate multiple OTP codes and check they're different
        codes = [EmailVerification.generate_otp() for _ in range(100)]
        unique_codes = set(codes)

        # Should have high uniqueness (allow some duplicates due to randomness)
        self.assertGreater(len(unique_codes), 95)

    def test_automatic_expiry_time_setting(self):
        """Test that expiry time is automatically set to 10 minutes from creation."""
        before_creation = timezone.now()
        verification = EmailVerification.objects.create(user=self.user)
        after_creation = timezone.now()

        expected_expiry_min = before_creation + timedelta(minutes=10)
        expected_expiry_max = after_creation + timedelta(minutes=10)

        self.assertGreaterEqual(verification.expires_at, expected_expiry_min)
        self.assertLessEqual(verification.expires_at, expected_expiry_max)

    def test_is_expired_method_false_when_not_expired(self):
        """Test is_expired returns False for non-expired verification."""
        verification = EmailVerification.objects.create(user=self.user)

        self.assertFalse(verification.is_expired())

    def test_is_expired_method_true_when_expired(self):
        """Test is_expired returns True for expired verification."""
        # Create verification with past expiry time
        past_time = timezone.now() - timedelta(minutes=1)
        verification = EmailVerification.objects.create(
            user=self.user, expires_at=past_time
        )

        self.assertTrue(verification.is_expired())

    def test_is_valid_method_for_fresh_verification(self):
        """Test is_valid returns True for fresh, unused verification."""
        verification = EmailVerification.objects.create(user=self.user)

        self.assertTrue(verification.is_valid())

    def test_is_valid_method_for_used_verification(self):
        """Test is_valid returns False for used verification."""
        verification = EmailVerification.objects.create(user=self.user)
        verification.is_used = True
        verification.save()

        self.assertFalse(verification.is_valid())

    def test_is_valid_method_for_expired_verification(self):
        """Test is_valid returns False for expired verification."""
        past_time = timezone.now() - timedelta(minutes=1)
        verification = EmailVerification.objects.create(
            user=self.user, expires_at=past_time
        )

        self.assertFalse(verification.is_valid())

    def test_mark_as_used_method(self):
        """Test mark_as_used method sets is_used flag."""
        verification = EmailVerification.objects.create(user=self.user)

        self.assertFalse(verification.is_used)
        verification.mark_as_used()

        # Refresh from database
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)

    def test_create_for_user_class_method(self):
        """Test create_for_user class method creates verification correctly."""
        verification = EmailVerification.create_for_user(self.user)

        self.assertEqual(verification.user, self.user)
        self.assertTrue(verification.is_valid())
        self.assertIsNotNone(verification.otp_code)

    def test_get_valid_otp_success(self):
        """Test get_valid_otp returns verification for valid code."""
        verification = EmailVerification.objects.create(user=self.user)
        otp_code = verification.otp_code

        found_verification = EmailVerification.get_valid_otp(self.user, otp_code)

        self.assertEqual(found_verification, verification)

    def test_get_valid_otp_wrong_code(self):
        """Test get_valid_otp returns None for wrong code."""
        EmailVerification.objects.create(user=self.user)

        found_verification = EmailVerification.get_valid_otp(self.user, "999999")

        self.assertIsNone(found_verification)

    def test_get_valid_otp_wrong_user(self):
        """Test get_valid_otp returns None for wrong user."""
        verification = EmailVerification.objects.create(user=self.user)
        otp_code = verification.otp_code

        found_verification = EmailVerification.get_valid_otp(self.other_user, otp_code)

        self.assertIsNone(found_verification)

    def test_get_valid_otp_expired_code(self):
        """Test get_valid_otp returns None for expired code."""
        past_time = timezone.now() - timedelta(minutes=1)
        verification = EmailVerification.objects.create(
            user=self.user, expires_at=past_time
        )

        found_verification = EmailVerification.get_valid_otp(
            self.user, verification.otp_code
        )

        self.assertIsNone(found_verification)

    def test_get_valid_otp_used_code(self):
        """Test get_valid_otp returns None for used code."""
        verification = EmailVerification.objects.create(user=self.user)
        verification.is_used = True
        verification.save()

        found_verification = EmailVerification.get_valid_otp(
            self.user, verification.otp_code
        )

        self.assertIsNone(found_verification)

    def test_string_representation(self):
        """Test __str__ method returns meaningful representation."""
        verification = EmailVerification.objects.create(user=self.user)

        str_repr = str(verification)

        self.assertIn(self.user.username, str_repr)
        self.assertIn(verification.otp_code, str_repr)
        self.assertIn("Valid", str_repr)

    def test_string_representation_used_verification(self):
        """Test __str__ method for used verification shows 'Used' status."""
        verification = EmailVerification.objects.create(user=self.user)
        verification.is_used = True
        verification.save()

        str_repr = str(verification)

        self.assertIn("Used", str_repr)

    def test_string_representation_expired_verification(self):
        """Test __str__ method for expired verification shows 'Expired' status."""
        past_time = timezone.now() - timedelta(minutes=1)
        verification = EmailVerification.objects.create(
            user=self.user, expires_at=past_time
        )

        str_repr = str(verification)

        self.assertIn("Expired", str_repr)

    def test_model_ordering(self):
        """Test that EmailVerification model orders by created_at descending."""
        # Create multiple verifications with slight time differences
        EmailVerification.objects.create(user=self.user)

        # Create a new user to ensure we can test ordering
        second_user = User.objects.create_user(
            username="testuser2", email="testuser2@example.com", password="testpass123"
        )
        EmailVerification.objects.create(user=second_user)

        # Get all verifications ordered by default (created_at descending)
        all_verifications = list(EmailVerification.objects.all())

        # The second verification should be first (newest)
        self.assertEqual(len(all_verifications), 2)
        # Verify ordering - second created should be first in list
        self.assertGreaterEqual(
            all_verifications[0].created_at, all_verifications[1].created_at
        )

    def test_user_cascade_deletion(self):
        """Test that EmailVerification is deleted when user is deleted."""
        verification = EmailVerification.objects.create(user=self.user)
        verification_id = verification.id

        # Delete the user
        self.user.delete()

        # Verification should also be deleted
        self.assertFalse(EmailVerification.objects.filter(id=verification_id).exists())

    def test_multiple_verifications_per_user(self):
        """Test that a user can have multiple verification records."""
        verification1 = EmailVerification.objects.create(user=self.user)
        verification2 = EmailVerification.objects.create(user=self.user)

        user_verifications = EmailVerification.objects.filter(user=self.user)

        self.assertEqual(user_verifications.count(), 2)
        self.assertIn(verification1, user_verifications)
        self.assertIn(verification2, user_verifications)

    def test_otp_code_manual_setting(self):
        """Test that OTP code can be manually set during creation."""
        custom_code = "123456"
        verification = EmailVerification.objects.create(
            user=self.user, otp_code=custom_code
        )

        self.assertEqual(verification.otp_code, custom_code)

    def test_expires_at_manual_setting(self):
        """Test that expiry time can be manually set during creation."""
        custom_expiry = timezone.now() + timedelta(hours=1)
        verification = EmailVerification.objects.create(
            user=self.user, expires_at=custom_expiry
        )

        self.assertEqual(verification.expires_at, custom_expiry)

    def test_verification_meta_attributes(self):
        """Test model meta attributes are set correctly."""
        meta = EmailVerification._meta

        self.assertEqual(meta.verbose_name, "Email Verification")
        self.assertEqual(meta.verbose_name_plural, "Email Verifications")
        self.assertEqual(meta.ordering, ["-created_at"])

    def test_related_name_functionality(self):
        """Test that the related_name 'email_verifications' works correctly."""
        verification1 = EmailVerification.objects.create(user=self.user)
        verification2 = EmailVerification.objects.create(user=self.user)

        user_verifications = self.user.email_verifications.all()

        self.assertEqual(user_verifications.count(), 2)
        self.assertIn(verification1, user_verifications)
        self.assertIn(verification2, user_verifications)
