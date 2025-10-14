from django.test import TestCase
from django.contrib.auth import get_user_model

from authentication.forms import (
    PasswordResetRequestForm,
    PasswordResetOTPForm,
    PasswordResetConfirmForm,
    ResendPasswordResetOTPForm,
)

User = get_user_model()


class PasswordResetFormsTests(TestCase):
    """
    Unit tests for password reset forms.
    """

    def setUp(self):
        """Set up test data for each test method."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    # PasswordResetRequestForm Tests
    def test_password_reset_request_form_valid_data(self):
        """Test form with valid email data."""
        form_data = {"email": "test@example.com"}
        form = PasswordResetRequestForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "test@example.com")

    def test_password_reset_request_form_email_normalization(self):
        """Test email is normalized (lowercase and stripped)."""
        form_data = {"email": "  TEST@EXAMPLE.COM  "}
        form = PasswordResetRequestForm(data=form_data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "test@example.com")

    def test_password_reset_request_form_invalid_email(self):
        """Test form with invalid email format."""
        form_data = {"email": "invalid-email"}
        form = PasswordResetRequestForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_reset_request_form_empty_email(self):
        """Test form with empty email."""
        form_data = {"email": ""}
        form = PasswordResetRequestForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_password_reset_request_form_max_length(self):
        """Test form with email exceeding max length."""
        long_email = "a" * 250 + "@example.com"  # Over 254 chars
        form_data = {"email": long_email}
        form = PasswordResetRequestForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    # PasswordResetOTPForm Tests
    def test_password_reset_otp_form_valid_data(self):
        """Test OTP form with valid data."""
        form_data = {"email": "test@example.com", "otp_code": "123456"}
        form = PasswordResetOTPForm(data=form_data, email="test@example.com")

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["otp_code"], "123456")
        self.assertEqual(form.cleaned_data["email"], "test@example.com")

    def test_password_reset_otp_form_prepopulated_email(self):
        """Test OTP form with prepopulated email."""
        form = PasswordResetOTPForm(email="test@example.com")

        self.assertEqual(form.fields["email"].initial, "test@example.com")

    def test_password_reset_otp_form_invalid_otp_length(self):
        """Test OTP form with invalid code length."""
        # Too short
        form_data = {"email": "test@example.com", "otp_code": "123"}
        form = PasswordResetOTPForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("otp_code", form.errors)

        # Too long
        form_data["otp_code"] = "1234567"
        form = PasswordResetOTPForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("otp_code", form.errors)

    def test_password_reset_otp_form_non_numeric_otp(self):
        """Test OTP form with non-numeric code."""
        form_data = {"email": "test@example.com", "otp_code": "abcdef"}
        form = PasswordResetOTPForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("otp_code", form.errors)

    def test_password_reset_otp_form_mixed_characters_otp(self):
        """Test OTP form with mixed alphanumeric code."""
        form_data = {"email": "test@example.com", "otp_code": "123abc"}
        form = PasswordResetOTPForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("otp_code", form.errors)

    def test_password_reset_otp_form_empty_otp(self):
        """Test OTP form with empty OTP code."""
        form_data = {"email": "test@example.com", "otp_code": ""}
        form = PasswordResetOTPForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("otp_code", form.errors)

    # PasswordResetConfirmForm Tests
    def test_password_reset_confirm_form_valid_data(self):
        """Test confirm form with valid passwords."""
        form_data = {
            "email": "test@example.com",
            "otp_code": "123456",
            "new_password": "newstrongpassword123",
            "confirm_password": "newstrongpassword123",
        }
        form = PasswordResetConfirmForm(
            data=form_data, email="test@example.com", otp_code="123456"
        )

        self.assertTrue(form.is_valid())

    def test_password_reset_confirm_form_password_mismatch(self):
        """Test confirm form with mismatched passwords."""
        form_data = {
            "email": "test@example.com",
            "otp_code": "123456",
            "new_password": "newstrongpassword123",
            "confirm_password": "differentpassword123",
        }
        form = PasswordResetConfirmForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("The two password fields must match", str(form.errors))

    def test_password_reset_confirm_form_weak_password(self):
        """Test confirm form with weak password."""
        form_data = {
            "email": "test@example.com",
            "otp_code": "123456",
            "new_password": "123",  # Too weak
            "confirm_password": "123",
        }
        form = PasswordResetConfirmForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("new_password", form.errors)

    def test_password_reset_confirm_form_common_password(self):
        """Test confirm form with common password."""
        form_data = {
            "email": "test@example.com",
            "otp_code": "123456",
            "new_password": "password123",  # Common password
            "confirm_password": "password123",
        }
        form = PasswordResetConfirmForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("new_password", form.errors)

    def test_password_reset_confirm_form_numeric_password(self):
        """Test confirm form with entirely numeric password."""
        form_data = {
            "email": "test@example.com",
            "otp_code": "123456",
            "new_password": "12345678",  # All numeric
            "confirm_password": "12345678",
        }
        form = PasswordResetConfirmForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("new_password", form.errors)

    def test_password_reset_confirm_form_prepopulated_fields(self):
        """Test confirm form with prepopulated hidden fields."""
        form = PasswordResetConfirmForm(email="test@example.com", otp_code="123456")

        self.assertEqual(form.fields["email"].initial, "test@example.com")
        self.assertEqual(form.fields["otp_code"].initial, "123456")

    def test_password_reset_confirm_form_empty_passwords(self):
        """Test confirm form with empty passwords."""
        form_data = {
            "email": "test@example.com",
            "otp_code": "123456",
            "new_password": "",
            "confirm_password": "",
        }
        form = PasswordResetConfirmForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("new_password", form.errors)
        self.assertIn("confirm_password", form.errors)

    # ResendPasswordResetOTPForm Tests
    def test_resend_password_reset_otp_form_valid(self):
        """Test resend OTP form with valid data."""
        form_data = {"email": "test@example.com"}
        form = ResendPasswordResetOTPForm(data=form_data, email="test@example.com")

        self.assertTrue(form.is_valid())

    def test_resend_password_reset_otp_form_prepopulated_email(self):
        """Test resend OTP form with prepopulated email."""
        form = ResendPasswordResetOTPForm(email="test@example.com")

        self.assertEqual(form.fields["email"].initial, "test@example.com")

    def test_resend_password_reset_otp_form_empty_email(self):
        """Test resend OTP form with empty email."""
        form_data = {"email": ""}
        form = ResendPasswordResetOTPForm(data=form_data)

        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    # Form Widget and Attributes Tests
    def test_password_reset_request_form_widget_attributes(self):
        """Test form widget attributes are correctly set."""
        form = PasswordResetRequestForm()

        email_widget = form.fields["email"].widget
        self.assertEqual(email_widget.attrs.get("autocomplete"), "email")
        self.assertIn("placeholder", email_widget.attrs)

    def test_password_reset_otp_form_widget_attributes(self):
        """Test OTP form widget attributes are correctly set."""
        form = PasswordResetOTPForm()

        otp_widget = form.fields["otp_code"].widget
        self.assertEqual(otp_widget.attrs.get("autocomplete"), "one-time-code")
        self.assertEqual(otp_widget.attrs.get("inputmode"), "numeric")
        self.assertEqual(otp_widget.attrs.get("pattern"), "[0-9]{6}")
        self.assertEqual(otp_widget.attrs.get("maxlength"), "6")

    def test_password_reset_confirm_form_widget_attributes(self):
        """Test confirm form widget attributes are correctly set."""
        form = PasswordResetConfirmForm()

        new_password_widget = form.fields["new_password"].widget
        confirm_password_widget = form.fields["confirm_password"].widget

        self.assertEqual(new_password_widget.attrs.get("autocomplete"), "new-password")
        self.assertEqual(
            confirm_password_widget.attrs.get("autocomplete"), "new-password"
        )

    def test_form_bootstrap_styling_applied(self):
        """Test that Bootstrap styling is applied to form fields."""
        forms_to_test = [
            PasswordResetRequestForm(),
            PasswordResetOTPForm(),
            PasswordResetConfirmForm(),
            ResendPasswordResetOTPForm(),
        ]

        for form in forms_to_test:
            for field_name, field in form.fields.items():
                # Skip hidden fields
                if field.widget.input_type != "hidden":
                    self.assertIn("form-control", field.widget.attrs.get("class", ""))

    def test_password_reset_otp_form_readonly_email(self):
        """Test that email field in OTP form is readonly."""
        form = PasswordResetOTPForm()

        email_widget = form.fields["email"].widget
        self.assertTrue(email_widget.attrs.get("readonly"))
