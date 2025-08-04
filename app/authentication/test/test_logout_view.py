from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpResponse

User = get_user_model()


class UserLogoutViewTests(TestCase):
    """
    Comprehensive test cases for user logout view.
    """

    def setUp(self):
        self.client: Client = Client()
        self.logout_url = reverse("authentication:logout")
        self.login_url = reverse("authentication:login")

        # Create a test user
        self.user: AbstractBaseUser = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="securepassword123",
        )

    def test_get_logout_view_requires_authentication(self) -> None:
        """
        Test that GET request to logout view requires authentication.
        """
        response: HttpResponse = self.client.get(self.logout_url)

        # Should redirect to login page
        self.assertEqual(
            response.status_code, 302, "Unauthenticated user should be redirected"
        )
        self.assertIn("login", response.url, "Should redirect to login page")

    def test_get_logout_view_with_authenticated_user(self) -> None:
        """
        Test GET request to logout view with authenticated user returns correct template.
        """
        # Login as user
        self.client.force_login(self.user)

        response: HttpResponse = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 200, "Response should be 200 OK")
        self.assertTemplateUsed(response, "authentication/logout.html")

    def test_post_logout_view_requires_authentication(self) -> None:
        """
        Test that POST request to logout view requires authentication.
        """
        response: HttpResponse = self.client.post(self.logout_url)

        # Should redirect to login page
        self.assertEqual(
            response.status_code, 302, "Unauthenticated user should be redirected"
        )
        self.assertIn("login", response.url, "Should redirect to login page")

    def test_post_logout_successful(self) -> None:
        """
        Test successful logout with POST request.
        """
        # Login as user first
        self.client.force_login(self.user)

        # Verify user is logged in
        response = self.client.get("/")
        self.assertTrue(
            response.wsgi_request.user.is_authenticated,
            "User should be authenticated before logout",
        )

        # Logout
        response: HttpResponse = self.client.post(self.logout_url)

        # Check redirect after successful logout
        self.assertEqual(
            response.status_code,
            302,
            "Response should be a redirect after successful logout",
        )
        self.assertEqual(response.url, self.login_url, "Should redirect to login page")

    def test_logout_success_message_displayed(self) -> None:
        """
        Test that success message is displayed after successful logout.
        """
        # Login as user first
        self.client.force_login(self.user)

        response: HttpResponse = self.client.post(self.logout_url, follow=True)

        # Check that success message is in messages
        messages = list(response.context["messages"])
        self.assertEqual(len(messages), 1, "Should have one message")
        self.assertEqual(
            str(messages[0]), "You have been logged out successfully, testuser."
        )
        self.assertEqual(messages[0].tags, "success", "Message should be success type")

    def test_logout_user_is_actually_logged_out(self) -> None:
        """
        Test that user is actually logged out after POST request.
        """
        # Login as user first
        self.client.force_login(self.user)

        # Verify user is logged in
        response = self.client.get("/")
        self.assertTrue(
            response.wsgi_request.user.is_authenticated,
            "User should be authenticated before logout",
        )

        # Logout
        self.client.post(self.logout_url)

        # Verify user is logged out
        response = self.client.get("/")
        self.assertFalse(
            response.wsgi_request.user.is_authenticated,
            "User should not be authenticated after logout",
        )

    def test_logout_view_uses_correct_template(self) -> None:
        """
        Test that the logout view uses the correct template.
        """
        from authentication.views import LogoutView

        view = LogoutView()
        self.assertEqual(
            view.template_name,
            "authentication/logout.html",
            "View should use correct template",
        )

    def test_logout_csrf_protection(self) -> None:
        """
        Test that CSRF protection is enabled for logout form.
        """
        # Login as user first
        self.client.force_login(self.user)

        # Test GET request includes CSRF token
        response: HttpResponse = self.client.get(self.logout_url)
        self.assertContains(
            response, "csrfmiddlewaretoken", msg_prefix="Form should contain CSRF token"
        )

        # Test POST request without CSRF token fails
        from django.test import Client as BaseClient

        csrf_client = BaseClient(enforce_csrf_checks=True)

        # Login the csrf_client as well
        csrf_client.force_login(self.user)

        response = csrf_client.post(self.logout_url)
        self.assertEqual(
            response.status_code, 403, "Request without CSRF token should be forbidden"
        )

    def test_logout_view_inheritance(self) -> None:
        """
        Test that the logout view properly inherits from required mixins.
        """
        from authentication.views import LogoutView
        from django.contrib.auth.mixins import LoginRequiredMixin
        from django.views.generic import View

        view = LogoutView()
        self.assertTrue(
            isinstance(view, LoginRequiredMixin),
            "View should inherit from LoginRequiredMixin",
        )
        self.assertTrue(isinstance(view, View), "View should inherit from View")

    def test_logout_get_method_only_shows_confirmation(self) -> None:
        """
        Test that GET request to logout only shows confirmation, doesn't actually log out.
        """
        # Login as user first
        self.client.force_login(self.user)

        # GET request to logout (should not log out, only show confirmation)
        response: HttpResponse = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, 200, "GET request should return 200 OK")
        self.assertTemplateUsed(response, "authentication/logout.html")

        # User should still be logged in after GET request
        response = self.client.get("/")
        self.assertTrue(
            response.wsgi_request.user.is_authenticated,
            "User should still be authenticated after GET request",
        )

    def test_logout_handles_anonymous_user_gracefully(self) -> None:
        """
        Test that logout view handles requests from anonymous users gracefully.
        """
        # Try to access logout without being logged in
        response: HttpResponse = self.client.get(self.logout_url)

        # Should redirect to login page (due to LoginRequiredMixin)
        self.assertEqual(
            response.status_code, 302, "Anonymous user should be redirected"
        )

        # Try POST request without being logged in
        response: HttpResponse = self.client.post(self.logout_url)

        # Should also redirect to login page
        self.assertEqual(
            response.status_code, 302, "Anonymous user POST should be redirected"
        )
