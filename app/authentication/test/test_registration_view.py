from typing import Dict, Any
from django.test import TestCase, Client
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth import get_user_model
from authentication.forms import CustomUserCreationForm

User = get_user_model()


class UserRegistrationViewTests(TestCase):
    """
    Comprehensive test cases for user registration view.
    """

    def setUp(self):
        self.client: Client = Client()
        self.register_url = reverse("authentication:register")
        self.login_url = reverse("authentication:login")

        # Create an existing user for testing conflicts
        self.existing_user: AbstractBaseUser = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="securepassword123",
        )

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
        self.assertEqual(
            response.status_code, 302, "Authenticated user should be redirected"
        )
        self.assertEqual(response.url, "/", "Should redirect to home page")

    def test_register_new_user_success(self) -> None:
        """
        Test successful user registration with valid data.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        # Check user doesn't exist before registration
        self.assertFalse(
            User.objects.filter(username="newuser").exists(),
            "User should not exist before registration",
        )

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        # Check redirect after successful registration
        self.assertEqual(
            response.status_code,
            302,
            "Response should be a redirect after successful registration",
        )
        # Should redirect to email verification page now
        expected_url = reverse("authentication:verify_email")
        self.assertEqual(
            response.url, expected_url, "Should redirect to email verification page"
        )

        # Check user was created in database
        self.assertTrue(
            User.objects.filter(username="newuser").exists(),
            "User should be created in the database",
        )

        # Verify user data
        created_user = User.objects.get(username="newuser")
        self.assertEqual(created_user.email, payload["email"], "Email should match")
        self.assertEqual(
            created_user.first_name, payload["first_name"], "First name should match"
        )
        self.assertEqual(
            created_user.last_name, payload["last_name"], "Last name should match"
        )

    def test_register_new_user_success_with_next_parameter(self) -> None:
        """
        Test successful registration with 'next' parameter redirects to specified URL.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        next_url = "/dashboard/"
        response: HttpResponse = self.client.post(
            f"{self.register_url}?next={next_url}", data=payload
        )

        self.assertEqual(response.status_code, 302, "Response should be a redirect")
        # With email verification required, should redirect to verification page first
        expected_url = reverse("authentication:verify_email")
        self.assertEqual(
            response.url, expected_url, "Should redirect to email verification first"
        )

    def test_register_with_duplicate_username(self) -> None:
        """
        Test registration with duplicate username fails appropriately.
        """
        payload: Dict[str, Any] = {
            "username": "existinguser",  # Same as existing user
            "first_name": "Duplicate",
            "last_name": "User",
            "email": "duplicate@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        self.assertEqual(
            response.status_code,
            200,
            "Response should be 200 OK for invalid registration",
        )
        self.assertTemplateUsed(response, "authentication/register.html")

        # Check form errors
        form = response.context["form"]
        self.assertTrue(form.errors, "Form should have errors")
        self.assertIn("username", form.errors, "Form should have username error")

        # Ensure no duplicate user was created
        self.assertEqual(
            User.objects.filter(username="existinguser").count(),
            1,
            "Should still have only one user with this username",
        )

    def test_register_with_duplicate_email(self) -> None:
        """
        Test registration with duplicate email fails appropriately.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "existing@example.com",  # Same as existing user
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        self.assertEqual(
            response.status_code,
            200,
            "Response should be 200 OK for invalid registration",
        )
        self.assertTemplateUsed(response, "authentication/register.html")

        # Check form errors
        form = response.context["form"]
        self.assertTrue(form.errors, "Form should have errors")
        self.assertIn("email", form.errors, "Form should have email error")

        # Ensure no user was created with duplicate email
        self.assertFalse(
            User.objects.filter(username="newuser").exists(),
            "User should not be created with duplicate email",
        )

    def test_register_with_mismatched_passwords(self) -> None:
        """
        Test registration with mismatched passwords fails appropriately.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "differentpassword123",
        }

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        self.assertEqual(
            response.status_code,
            200,
            "Response should be 200 OK for invalid registration",
        )
        self.assertTemplateUsed(response, "authentication/register.html")

        # Check form errors
        form = response.context["form"]
        self.assertTrue(form.errors, "Form should have errors")
        self.assertIn("password2", form.errors, "Form should have password2 error")

        # Ensure no user was created
        self.assertFalse(
            User.objects.filter(username="newuser").exists(),
            "User should not be created with mismatched passwords",
        )

    def test_register_with_weak_password(self) -> None:
        """
        Test registration with weak password fails appropriately.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "123",  # Too short and weak
            "password2": "123",
        }

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        self.assertEqual(
            response.status_code,
            200,
            "Response should be 200 OK for invalid registration",
        )
        self.assertTemplateUsed(response, "authentication/register.html")

        # Check form errors
        form = response.context["form"]
        self.assertTrue(form.errors, "Form should have errors")
        self.assertIn("password1", form.errors, "Form should have password1 error")

        # Ensure no user was created
        self.assertFalse(
            User.objects.filter(username="newuser").exists(),
            "User should not be created with weak password",
        )

    def test_register_with_honeypot_field(self) -> None:
        """
        Test registration with honeypot field filled is rejected.
        """
        payload: Dict[str, Any] = {
            "username": "botuser",
            "first_name": "Bot",
            "last_name": "User",
            "email": "bot@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
            "honeypot": "spam_content",  # Bot detected
        }

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        self.assertEqual(
            response.status_code,
            200,
            "Response should be 200 OK for invalid registration",
        )
        self.assertTemplateUsed(response, "authentication/register.html")

        # Check form errors
        form = response.context["form"]
        self.assertTrue(form.errors, "Form should have errors")
        self.assertIn("honeypot", form.errors, "Form should have honeypot error")

        # Ensure no user was created
        self.assertFalse(
            User.objects.filter(username="botuser").exists(),
            "Bot user should not be created",
        )

    def test_register_with_missing_required_fields(self) -> None:
        """
        Test registration with missing required fields fails appropriately.
        """
        payload: Dict[str, Any] = {
            "username": "",  # Missing
            "first_name": "",  # Missing
            "last_name": "User",
            "email": "",  # Missing
            "password1": "",  # Missing
            "password2": "",  # Missing
        }

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        self.assertEqual(
            response.status_code,
            200,
            "Response should be 200 OK for invalid registration",
        )
        self.assertTemplateUsed(response, "authentication/register.html")

        # Check that form has errors for required fields
        form = response.context["form"]
        self.assertIn("username", form.errors, "Username should have validation error")
        self.assertIn(
            "first_name", form.errors, "First name should have validation error"
        )
        self.assertIn("email", form.errors, "Email should have validation error")
        self.assertIn(
            "password1", form.errors, "Password1 should have validation error"
        )

    def test_register_with_invalid_email_format(self) -> None:
        """
        Test registration with invalid email format fails appropriately.
        """
        invalid_emails = [
            "invalid-email",
            "test@",
            "@example.com",
            "test..test@example.com",
        ]

        for invalid_email in invalid_emails:
            with self.subTest(email=invalid_email):
                payload: Dict[str, Any] = {
                    "username": f'testuser_{invalid_email.replace("@", "_at_").replace(".", "_dot_")}',
                    "first_name": "Test",
                    "last_name": "User",
                    "email": invalid_email,
                    "password1": "securepassword123",
                    "password2": "securepassword123",
                }

                response: HttpResponse = self.client.post(
                    self.register_url, data=payload
                )

                self.assertEqual(
                    response.status_code,
                    200,
                    f"Response should be 200 OK for invalid email: {invalid_email}",
                )

                # Check form errors
                form = response.context["form"]
                self.assertTrue(
                    form.errors,
                    f"Form should have errors for invalid email: {invalid_email}",
                )
                self.assertIn(
                    "email",
                    form.errors,
                    f"Form should have email error for: {invalid_email}",
                )

    def test_register_success_message_displayed(self) -> None:
        """
        Test that success message is displayed after successful registration.
        """
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        response: HttpResponse = self.client.post(
            self.register_url, data=payload, follow=True
        )

        # Check that success message is in messages
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1, "Should have one message")
        # Updated for email verification flow
        expected_message = "Account created for newuser! Please check your email for the verification code."
        self.assertEqual(str(messages[0]), expected_message)
        self.assertEqual(messages[0].tags, "success", "Message should be success type")

    def test_register_error_message_for_honeypot(self) -> None:
        """
        Test that error message is displayed for honeypot detection.
        """
        payload: Dict[str, Any] = {
            "username": "botuser",
            "first_name": "Bot",
            "last_name": "User",
            "email": "bot@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
            "honeypot": "spam_content",
        }

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        # Check that error message is in messages
        messages = list(response.context["messages"])
        self.assertTrue(
            any("Detected spam submission." in str(msg) for msg in messages),
            "Should have spam detection message",
        )

    def test_register_error_message_for_form_errors(self) -> None:
        """
        Test that error message is displayed for general form errors.
        """
        payload: Dict[str, Any] = {
            "username": "",  # Invalid
            "first_name": "Test",
            "last_name": "User",
            "email": "invalid-email",  # Invalid
            "password1": "securepassword123",
            "password2": "differentpassword123",  # Mismatched
        }

        response: HttpResponse = self.client.post(self.register_url, data=payload)

        # Check that error message is in messages
        messages = list(response.context["messages"])
        self.assertTrue(
            any("Please correct the errors below." in str(msg) for msg in messages),
            "Should have general error message",
        )

    def test_register_form_context_data(self) -> None:
        """
        Test that the registration view provides correct context data.
        """
        response: HttpResponse = self.client.get(self.register_url)

        self.assertIn("form", response.context, "Context should contain form")
        self.assertIsInstance(
            response.context["form"],
            CustomUserCreationForm,
            "Form should be CustomUserCreationForm",
        )

        # Check that form fields are properly rendered
        form_html = str(response.context["form"])
        self.assertIn("username", form_html, "Form should contain username field")
        self.assertIn("email", form_html, "Form should contain email field")
        self.assertIn("first_name", form_html, "Form should contain first_name field")
        self.assertIn("last_name", form_html, "Form should contain last_name field")
        self.assertIn("password1", form_html, "Form should contain password1 field")
        self.assertIn("password2", form_html, "Form should contain password2 field")

    def test_register_view_uses_correct_form_class(self) -> None:
        """
        Test that the registration view uses the correct form class.
        """
        from authentication.views import RegisterView

        view = RegisterView()
        self.assertEqual(
            view.form_class,
            CustomUserCreationForm,
            "View should use CustomUserCreationForm",
        )
        self.assertEqual(
            view.template_name,
            "authentication/register.html",
            "View should use correct template",
        )
        # The success URL should now be email verification, not login
        expected_url = reverse("authentication:verify_email")
        self.assertEqual(
            str(view.success_url),
            expected_url,
            "View should redirect to email verification after registration",
        )

    def test_register_csrf_protection(self) -> None:
        """
        Test that CSRF protection is enabled for registration form.
        """
        # Test GET request includes CSRF token
        response: HttpResponse = self.client.get(self.register_url)
        self.assertContains(
            response, "csrfmiddlewaretoken", msg_prefix="Form should contain CSRF token"
        )

        # Test POST request without CSRF token fails
        payload: Dict[str, Any] = {
            "username": "newuser",
            "first_name": "New",
            "last_name": "User",
            "email": "newuser@example.com",
            "password1": "securepassword123",
            "password2": "securepassword123",
        }

        # Disable CSRF for this client temporarily
        from django.test import Client as BaseClient

        csrf_client = BaseClient(enforce_csrf_checks=True)
        response = csrf_client.post(self.register_url, data=payload)
        self.assertEqual(
            response.status_code, 403, "Request without CSRF token should be forbidden"
        )
