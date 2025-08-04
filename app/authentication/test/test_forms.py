from typing import Dict, Any
from django.test import TestCase
from django.forms import Form
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth import get_user_model
from authentication.forms import CustomUserCreationForm, CustomAuthenticationForm

User = get_user_model()


class UserCreationFormTests(TestCase):
    """
    Test cases for user creation form.
    """

    def test_form_valid(self) -> None:
        """
        Test the user creation form with valid data.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertTrue(form.is_valid(), "Form should be valid with correct data")

    def test_register_form_invalid(self) -> None:
        """
        Test the user registration form with invalid data.
        """
        payload: Dict[str, Any] = {
            "username": "",
            "email": "invalid-email",
            "password1": "short",
            "password2": "different",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(form.is_valid(), "Form should be invalid with incorrect data")

    def test_register_form_honeypot(self) -> None:
        """
        Test the honeypot field in the registration form.
        """
        payload: Dict[str, Any] = {
            "username": "honeypotuser",
            "email": "honeypotuser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
            "honeypot": "unexpected_value",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(form.is_valid(), "Form should be invalid with honeypot filled")

    def test_register_form_new_user_success(self) -> None:
        """
        Test successful user registration.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertTrue(form.is_valid(), "Form should be valid before saving")
        user: AbstractBaseUser = form.save()
        self.assertIsNotNone(user, "User should be created successfully")
        self.assertEqual(
            user.username,
            payload["username"],
            "Username should match the submitted data",
        )
        self.assertEqual(
            user.email, payload["email"], "Email should match the submitted data"
        )
        self.assertEqual(
            user.first_name,
            payload["first_name"],
            "First name should match the submitted data",
        )
        self.assertEqual(
            user.last_name,
            payload["last_name"],
            "Last name should match the submitted data",
        )

    def test_form_duplicate_email_validation(self) -> None:
        """
        Test the user creation form with an existing email.
        """
        User.objects.create_user(
            username="existinguser",
            email="existinguser@example.com",
            password="securepassword123",
        )

        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "existinguser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(form.is_valid(), "Form should be invalid with duplicate email")

    def test_form_password_too_short_validation(self) -> None:
        """
        Test the user creation form with a too short password.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "short",
            "password2": "short",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(
            form.is_valid(), "Form should be invalid with too short password"
        )

    def test_form_password_mismatch_validation(self) -> None:
        """
        Test the user creation form with mismatched passwords.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "differentpassword123",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(
            form.is_valid(), "Form should be invalid with mismatched passwords"
        )

    def test_form_placeholders(self) -> None:
        """
        Test that placeholders are set correctly in the form.
        """
        form: Form = CustomUserCreationForm()
        expected_placeholders: Dict[str, str] = {
            "username": "Choose a username",
            "email": "Enter your email",
            "first_name": "First name",
            "last_name": "Last name",
            "password1": "Enter password",
            "password2": "Confirm password",
        }

        for field_name, expected_placeholder in expected_placeholders.items():
            actual_placeholder = form.fields[field_name].widget.attrs.get("placeholder")
            self.assertEqual(
                actual_placeholder,
                expected_placeholder,
                f"Placeholder for {field_name} should match expected value",
            )

    def test_form_bootstrap_styling(self) -> None:
        """
        Test that Bootstrap form-control class is applied to all fields.
        """
        form: Form = CustomUserCreationForm()
        for field_name, field in form.fields.items():
            if field_name != "honeypot":  # Honeypot field is hidden
                field_class = field.widget.attrs.get("class", "")
                self.assertIn(
                    "form-control",
                    field_class,
                    f"Bootstrap form-control class should be applied to {field_name}",
                )

    def test_form_help_text(self) -> None:
        """
        Test that help text is set correctly for form fields.
        """
        form: Form = CustomUserCreationForm()
        expected_help_texts: Dict[str, str] = {
            "email": "Enter a valid email address",
            "first_name": "Enter your first name",
            "last_name": "Enter your last name",
        }

        for field_name, expected_help_text in expected_help_texts.items():
            actual_help_text = form.fields[field_name].help_text
            self.assertEqual(
                actual_help_text,
                expected_help_text,
                f"Help text for {field_name} should match expected value",
            )

    def test_form_required_fields(self) -> None:
        """
        Test that required fields are properly marked as required.
        """
        form: Form = CustomUserCreationForm()
        required_fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]

        for field_name in required_fields:
            self.assertTrue(
                form.fields[field_name].required, f"{field_name} should be required"
            )

        # Honeypot should not be required
        self.assertFalse(
            form.fields["honeypot"].required, "Honeypot field should not be required"
        )

    def test_form_with_whitespace_only_data(self) -> None:
        """
        Test form validation with whitespace-only data.
        """
        payload: Dict[str, Any] = {
            "username": "   ",
            "first_name": "   ",
            "last_name": "   ",
            "email": "   ",
            "password1": "   ",
            "password2": "   ",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(
            form.is_valid(), "Form should be invalid with whitespace-only data"
        )

    def test_form_email_validation_detailed(self) -> None:
        """
        Test detailed email validation scenarios.
        """
        invalid_emails = [
            "invalid-email",
            "test@",
            "@example.com",
            "test..test@example.com",
            "test@example",
            "",
        ]

        for invalid_email in invalid_emails:
            payload: Dict[str, Any] = {
                "username": "testuser",
                "first_name": "Test",
                "last_name": "User",
                "email": invalid_email,
                "password1": "securepassword123",
                "password2": "securepassword123",
            }

            form: Form = CustomUserCreationForm(data=payload)
            self.assertFalse(
                form.is_valid(), f"Form should be invalid with email: {invalid_email}"
            )

    def test_form_username_validation(self) -> None:
        """
        Test username validation including edge cases.
        """
        # Test empty username
        payload: Dict[str, Any] = {
            "username": "",
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(form.is_valid(), "Form should be invalid with empty username")

    def test_form_commit_false_save(self) -> None:
        """
        Test that save(commit=False) returns an unsaved user instance.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertTrue(form.is_valid(), "Form should be valid")

        user: AbstractBaseUser = form.save(commit=False)
        self.assertIsNotNone(user, "User instance should be created")

        # Check that the user is not saved to the database yet
        self.assertFalse(
            User.objects.filter(username="newuser").exists(),
            "User should not be saved to database yet",
        )

        # Now save to database
        user.save()
        self.assertTrue(
            User.objects.filter(username="newuser").exists(),
            "User should now be saved to database",
        )

    def test_form_validation_error_messages(self) -> None:
        """
        Test that proper error messages are displayed for validation failures.
        """
        # Test duplicate email error message
        User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="securepassword123",
        )

        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "existing@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(form.is_valid(), "Form should be invalid with duplicate email")
        self.assertIn("email", form.errors, "Form should have email field error")
        self.assertIn(
            "A user with that email already exists.", str(form.errors["email"])
        )

    def test_form_honeypot_error_message(self) -> None:
        """
        Test that proper error message is displayed for honeypot validation failure.
        """
        payload: Dict[str, Any] = {
            "username": "honeypotuser",
            "first_name": "Honeypot",
            "last_name": "User",
            "email": "honeypot@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
            "honeypot": "spam_content",
        }

        form: Form = CustomUserCreationForm(data=payload)
        self.assertFalse(form.is_valid(), "Form should be invalid with honeypot filled")
        self.assertIn("honeypot", form.errors, "Form should have honeypot field error")
        self.assertIn("Detected spam submission.", str(form.errors["honeypot"]))

    def test_form_field_max_lengths(self) -> None:
        """
        Test that form fields respect their maximum length constraints.
        """
        form: Form = CustomUserCreationForm()

        # Check max lengths for char fields
        self.assertEqual(
            form.fields["first_name"].max_length,
            30,
            "First name should have max length of 30",
        )
        self.assertEqual(
            form.fields["last_name"].max_length,
            30,
            "Last name should have max length of 30",
        )

    def test_form_clean_methods_called(self) -> None:
        """
        Test that custom clean methods are properly called during validation.
        """
        # Test clean_email is called
        User.objects.create_user(
            username="testuser", email="test@example.com", password="securepassword123"
        )

        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "test@example.com",  # Duplicate email
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        form: Form = CustomUserCreationForm(data=payload)
        form.is_valid()  # Trigger validation

        # Check that clean_email was called and validation failed
        self.assertIn("email", form.errors)

        # Test clean_honeypot is called
        payload_honeypot: Dict[str, Any] = {
            "username": "testuser2",
            "first_name": "Test",
            "last_name": "User",
            "email": "test2@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
            "honeypot": "bot_content",
        }

        form_honeypot: Form = CustomUserCreationForm(data=payload_honeypot)
        form_honeypot.is_valid()  # Trigger validation

        # Check that clean_honeypot was called and validation failed
        self.assertIn("honeypot", form_honeypot.errors)

    def test_form_meta_configuration(self) -> None:
        """
        Test that the form's Meta class is properly configured.
        """
        form: Form = CustomUserCreationForm()

        # Check that the form uses the correct model
        self.assertEqual(
            form._meta.model, User, "Form should use the correct User model"
        )

        # Check that the form includes all expected fields
        expected_fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "password1",
            "password2",
        )
        self.assertEqual(
            form._meta.fields,
            expected_fields,
            "Form should include all expected fields in correct order",
        )

    def test_form_inheritance(self) -> None:
        """
        Test that the form properly inherits from expected classes.
        """
        form: Form = CustomUserCreationForm()

        # Check inheritance from UserCreationForm
        from django.contrib.auth.forms import UserCreationForm

        self.assertTrue(
            isinstance(form, UserCreationForm),
            "Form should inherit from UserCreationForm",
        )

        # Check inheritance from BootstrapFormMixin
        from authentication.mixins import BootstrapFormMixin

        self.assertTrue(
            isinstance(form, BootstrapFormMixin),
            "Form should inherit from BootstrapFormMixin",
        )


class UserAuthenticationFormTests(TestCase):
    """
    Test cases for user authentication form.
    """

    def setUp(self):
        self.user: AbstractBaseUser = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="securepassword123",
        )

    def test_authentication_form_valid(self) -> None:
        """
        Test the authentication form with valid credentials.
        """
        payload: Dict[str, Any] = {
            "username": "testuser",
            "password": "securepassword123",
        }

        form: Form = CustomAuthenticationForm(data=payload)
        self.assertTrue(
            form.is_valid(), "Form should be valid with correct credentials"
        )

    def test_authentication_form_invalid_username(self) -> None:
        """
        Test the authentication form with invalid username.
        """
        payload: Dict[str, Any] = {
            "username": "wronguser",
            "password": "securepassword123",
        }

        form: Form = CustomAuthenticationForm(data=payload)
        self.assertFalse(form.is_valid(), "Form should be invalid with wrong username")

    def test_authentication_form_invalid_password(self) -> None:
        """
        Test the authentication form with invalid password.
        """
        payload: Dict[str, Any] = {"username": "testuser", "password": "wrongpassword"}

        form: Form = CustomAuthenticationForm(data=payload)
        self.assertFalse(form.is_valid(), "Form should be invalid with wrong password")

    def test_authentication_form_empty_credentials(self) -> None:
        """
        Test the authentication form with empty credentials.
        """
        payload: Dict[str, Any] = {"username": "", "password": ""}

        form: Form = CustomAuthenticationForm(data=payload)
        self.assertFalse(
            form.is_valid(), "Form should be invalid with empty credentials"
        )

    def test_authentication_form_placeholders(self) -> None:
        """
        Test that placeholders are set correctly in the authentication form.
        """
        form: Form = CustomAuthenticationForm()
        expected_placeholders: Dict[str, str] = {
            "username": "Username",
            "password": "Password",
        }

        for field_name, expected_placeholder in expected_placeholders.items():
            actual_placeholder = form.fields[field_name].widget.attrs.get("placeholder")
            self.assertEqual(
                actual_placeholder,
                expected_placeholder,
                f"Placeholder for {field_name} should match expected value",
            )

    def test_authentication_form_bootstrap_styling(self) -> None:
        """
        Test that Bootstrap form-control class is applied to authentication form fields.
        """
        form: Form = CustomAuthenticationForm()
        for field_name, field in form.fields.items():
            field_class = field.widget.attrs.get("class", "")
            self.assertIn(
                "form-control",
                field_class,
                f"Bootstrap form-control class should be applied to {field_name}",
            )

    def test_authentication_form_get_user(self) -> None:
        """
        Test that the authentication form returns the correct user after validation.
        """
        payload: Dict[str, Any] = {
            "username": "testuser",
            "password": "securepassword123",
        }

        form: Form = CustomAuthenticationForm(data=payload)
        self.assertTrue(
            form.is_valid(), "Form should be valid with correct credentials"
        )

        authenticated_user = form.get_user()
        self.assertEqual(
            authenticated_user,
            self.user,
            "Form should return the correct user instance",
        )
        self.assertEqual(
            authenticated_user.username,
            "testuser",
            "Authenticated user should have correct username",
        )
