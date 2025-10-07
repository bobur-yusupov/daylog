from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from unittest.mock import patch, MagicMock

from authentication.forms import OTPVerificationForm, ResendOTPForm
from authentication.models import EmailVerification

User = get_user_model()


class OTPVerificationFormTests(TestCase):
    """
    Unit tests for OTP verification form validation and functionality.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_email_verified=False
        )
        
        self.verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="123456"
        )

    def test_form_initialization_without_user(self):
        """Test form initialization without user parameter."""
        form = OTPVerificationForm()
        
        self.assertIsNone(form.user)
        self.assertIn('otp_code', form.fields)

    def test_form_initialization_with_user(self):
        """Test form initialization with user parameter."""
        form = OTPVerificationForm(user=self.user)
        
        self.assertEqual(form.user, self.user)

    def test_form_field_attributes(self):
        """Test that form field has correct attributes for UX."""
        form = OTPVerificationForm()
        otp_field = form.fields['otp_code']
        widget_attrs = otp_field.widget.attrs
        
        # Check required attributes for good UX
        self.assertEqual(otp_field.max_length, 6)
        self.assertEqual(otp_field.min_length, 6)
        self.assertTrue(otp_field.required)
        # Check for actual CSS classes used in the form
        # Note: BootstrapFormMixin overwrites the class with just 'form-control'
        self.assertIn('form-control', widget_attrs.get('class', ''))
        self.assertEqual(widget_attrs.get('autocomplete'), 'one-time-code')
        self.assertEqual(widget_attrs.get('inputmode'), 'numeric')
        self.assertEqual(widget_attrs.get('pattern'), '[0-9]{6}')
        self.assertEqual(widget_attrs.get('maxlength'), '6')

    def test_valid_otp_code_validation(self):
        """Test validation with valid 6-digit OTP code."""
        form_data = {'otp_code': '123456'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['otp_code'], '123456')

    def test_empty_otp_code_validation(self):
        """Test validation fails for empty OTP code."""
        form_data = {'otp_code': ''}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('otp_code', form.errors)

    def test_short_otp_code_validation(self):
        """Test validation fails for OTP code shorter than 6 digits."""
        form_data = {'otp_code': '12345'}  # 5 digits
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('otp_code', form.errors)
        # Check for validation message (could be Django's built-in or custom message)
        error_msg = str(form.errors['otp_code'])
        validation_passed = (
            'Please enter a valid 6-digit code' in error_msg or
            'Ensure this value has at least 6 characters' in error_msg
        )
        self.assertTrue(validation_passed, f"Expected validation error, got: {error_msg}")

    def test_long_otp_code_validation(self):
        """Test validation fails for OTP code longer than 6 digits."""
        form_data = {'otp_code': '1234567'}  # 7 digits
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('otp_code', form.errors)

    def test_non_numeric_otp_code_validation(self):
        """Test validation fails for non-numeric OTP code."""
        form_data = {'otp_code': 'abcdef'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('otp_code', form.errors)
        self.assertIn('valid 6-digit code', str(form.errors['otp_code']))

    def test_mixed_alphanumeric_otp_code_validation(self):
        """Test validation fails for mixed alphanumeric OTP code."""
        form_data = {'otp_code': '12ab56'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('otp_code', form.errors)

    def test_otp_code_with_spaces_validation(self):
        """Test validation fails for OTP code with spaces."""
        form_data = {'otp_code': '12 34 56'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('otp_code', form.errors)

    def test_valid_otp_code_validation_without_user(self):
        """Test validation works without user for basic format check."""
        form_data = {'otp_code': '123456'}
        form = OTPVerificationForm(data=form_data)  # No user
        
        self.assertTrue(form.is_valid())

    def test_invalid_otp_code_with_user_validation(self):
        """Test validation fails for invalid OTP code when user is provided."""
        form_data = {'otp_code': '999999'}  # Wrong code
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('otp_code', form.errors)
        self.assertIn('Invalid or expired verification code', str(form.errors['otp_code']))

    def test_expired_otp_code_validation(self):
        """Test validation fails for expired OTP code."""
        # Mark verification as expired
        self.verification.is_used = True
        self.verification.save()
        
        form_data = {'otp_code': '123456'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())
        self.assertIn('otp_code', form.errors)

    def test_verify_otp_success(self):
        """Test verify_otp method succeeds with valid data."""
        form_data = {'otp_code': '123456'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid())
        result = form.verify_otp(self.user)
        
        self.assertTrue(result)
        
        # Check that user is now verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        
        # Check that verification is marked as used
        self.verification.refresh_from_db()
        self.assertTrue(self.verification.is_used)

    def test_verify_otp_failure_invalid_form(self):
        """Test verify_otp method fails with invalid form."""
        form_data = {'otp_code': '12345'}  # Invalid length
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        result = form.verify_otp(self.user)
        
        self.assertFalse(result)
        
        # User should remain unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_verify_otp_failure_wrong_code(self):
        """Test verify_otp method fails with wrong OTP code."""
        form_data = {'otp_code': '999999'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        result = form.verify_otp(self.user)
        
        self.assertFalse(result)
        
        # User should remain unverified
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_verify_otp_with_different_user(self):
        """Test verify_otp method with different user than form initialization should fail."""
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="testpass123",
            is_email_verified=False
        )
        other_verification = EmailVerification.objects.create(
            user=other_user,
            otp_code="654321"
        )
        
        form_data = {'otp_code': '654321'}
        form = OTPVerificationForm(data=form_data, user=self.user)  # Different user
        
        # This should fail because the form validates against self.user, not other_user
        result = form.verify_otp(other_user)
        
        self.assertFalse(result)
        
        # Other user should remain unverified
        other_user.refresh_from_db()
        self.assertFalse(other_user.is_email_verified)

    def test_bootstrap_styling_applied(self):
        """Test that Bootstrap styling is applied to form fields."""
        form = OTPVerificationForm()
        
        # This tests the BootstrapFormMixin functionality
        # The exact implementation depends on your BootstrapFormMixin
        otp_field = form.fields['otp_code']
        self.assertIn('form-control', otp_field.widget.attrs.get('class', ''))


class ResendOTPFormTests(TestCase):
    """
    Unit tests for ResendOTPForm.
    """

    def test_resend_form_initialization(self):
        """Test ResendOTPForm initializes correctly."""
        form = ResendOTPForm()
        
        # Should have no fields since it's just for CSRF protection
        self.assertEqual(len(form.fields), 0)

    def test_resend_form_is_always_valid(self):
        """Test ResendOTPForm is always valid (no fields to validate)."""
        form = ResendOTPForm(data={})
        
        self.assertTrue(form.is_valid())

    def test_resend_form_with_data(self):
        """Test ResendOTPForm with arbitrary data (should be ignored)."""
        form = ResendOTPForm(data={'some_field': 'some_value'})
        
        # Should still be valid as it ignores extra data
        self.assertTrue(form.is_valid())


class OTPFormIntegrationTests(TestCase):
    """
    Integration tests for OTP forms with related models.
    """

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="integrationuser",
            email="integration@example.com",
            password="testpass123",
            is_email_verified=False
        )

    def test_form_validation_with_multiple_verifications(self):
        """Test form validation when user has multiple verification records."""
        # Create multiple verifications
        old_verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="111111",
            is_used=True  # Old, used verification
        )
        
        current_verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="222222"  # Current, valid verification
        )
        
        # Form should validate with current verification
        form_data = {'otp_code': '222222'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid())
        
        # Should fail with old verification code
        form_data = {'otp_code': '111111'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertFalse(form.is_valid())

    def test_form_user_verification_status_update(self):
        """Test that form properly updates user verification status."""
        verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="333333"
        )
        
        # User should start unverified
        self.assertFalse(self.user.is_email_verified)
        
        # Verify OTP
        form_data = {'otp_code': '333333'}
        form = OTPVerificationForm(data=form_data, user=self.user)
        
        self.assertTrue(form.is_valid())
        result = form.verify_otp(self.user)
        
        self.assertTrue(result)
        
        # User should now be verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        
        # Verification should be marked as used
        verification.refresh_from_db()
        self.assertTrue(verification.is_used)

    def test_concurrent_verification_attempts(self):
        """Test behavior with concurrent verification attempts."""
        verification = EmailVerification.objects.create(
            user=self.user,
            otp_code="444444"
        )
        
        # First verification attempt
        form1_data = {'otp_code': '444444'}
        form1 = OTPVerificationForm(data=form1_data, user=self.user)
        
        # Second verification attempt (concurrent)
        form2_data = {'otp_code': '444444'}
        form2 = OTPVerificationForm(data=form2_data, user=self.user)
        
        # Both should validate initially
        self.assertTrue(form1.is_valid())
        self.assertTrue(form2.is_valid())
        
        # First verification should succeed
        result1 = form1.verify_otp(self.user)
        self.assertTrue(result1)
        
        # Second verification should fail (code already used)
        result2 = form2.verify_otp(self.user)
        self.assertFalse(result2)