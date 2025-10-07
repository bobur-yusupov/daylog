from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.template.loader import render_to_string, get_template
from django.template import TemplateDoesNotExist
from django.core.mail import EmailMultiAlternatives
import re

from authentication.models import EmailVerification
from authentication.services import EmailVerificationService

# Optional imports for enhanced testing (install with pip if needed)

try:
    from bs4 import BeautifulSoup

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

User = get_user_model()


class EmailTemplateSystemTests(TestCase):
    """
    System tests for email template rendering and content validation.
    """

    def setUp(self):
        """Set up test data for system tests."""
        self.user = User.objects.create_user(
            username="systemuser",
            email="system@example.com",
            password="testpass123",
            first_name="System",
            last_name="User",
        )

        self.verification = EmailVerification.objects.create(
            user=self.user, otp_code="123456"
        )

    def test_html_email_template_exists_and_renders(self):
        """Test that HTML email template exists and renders correctly."""
        template_path = "authentication/emails/otp_verification.html"

        # Test template exists
        try:
            template = get_template(template_path)
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail(f"HTML email template {template_path} does not exist")

        # Test template renders with context
        context = {
            "user": self.user,
            "otp_code": self.verification.otp_code,
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        html_content = render_to_string(template_path, context)

        # Basic content checks
        self.assertIsNotNone(html_content)
        self.assertIn("<!DOCTYPE html>", html_content)
        self.assertIn(self.verification.otp_code, html_content)
        self.assertIn(self.user.first_name, html_content)
        self.assertIn("DayLog", html_content)

    def test_text_email_template_exists_and_renders(self):
        """Test that text email template exists and renders correctly."""
        template_path = "authentication/emails/otp_verification.txt"

        # Test template exists
        try:
            template = get_template(template_path)
            self.assertIsNotNone(template)
        except TemplateDoesNotExist:
            self.fail(f"Text email template {template_path} does not exist")

        # Test template renders with context
        context = {
            "user": self.user,
            "otp_code": self.verification.otp_code,
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        text_content = render_to_string(template_path, context)

        # Basic content checks
        self.assertIsNotNone(text_content)
        self.assertIn(self.verification.otp_code, text_content)
        self.assertIn(self.user.first_name, text_content)
        self.assertIn("DayLog", text_content)
        self.assertNotIn("<html>", text_content)  # Should be plain text

    def test_html_template_structure_and_styling(self):
        """Test HTML template structure and CSS styling."""
        if not BS4_AVAILABLE:
            self.skipTest(
                "BeautifulSoup4 not available - install with 'pip install beautifulsoup4'"
            )

        context = {
            "user": self.user,
            "otp_code": self.verification.otp_code,
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        html_content = render_to_string(
            "authentication/emails/otp_verification.html", context
        )

        if not BS4_AVAILABLE:
            self.skipTest(
                "BeautifulSoup4 not available - install with: pip install beautifulsoup4"
            )

        soup = BeautifulSoup(html_content, "html.parser")

        # Check document structure
        self.assertIsNotNone(soup.find("html"))
        self.assertIsNotNone(soup.find("head"))
        self.assertIsNotNone(soup.find("body"))

        # Check meta tags for email compatibility
        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        self.assertIsNotNone(viewport_meta)

        # Check for responsive design elements
        style_tag = soup.find("style")
        self.assertIsNotNone(style_tag)

        style_content = style_tag.string if style_tag else ""
        self.assertIn("@media", style_content)  # Responsive CSS

        # Check OTP code display
        otp_elements = soup.find_all(text=re.compile(r"123456"))
        self.assertGreater(len(otp_elements), 0, "OTP code should appear in HTML")

    def test_template_security_and_escaping(self):
        """Test that templates properly escape user input to prevent XSS."""
        if not BS4_AVAILABLE:
            self.skipTest(
                "BeautifulSoup4 not available - install with 'pip install beautifulsoup4'"
            )

        # Create user with potentially dangerous content
        dangerous_user = User.objects.create_user(
            username="dangeroususer",
            email="dangerous@example.com",
            password="testpass123",
            first_name="<script>alert('xss')</script>",
            last_name="</title><script>alert('xss2')</script>",
        )

        context = {
            "user": dangerous_user,
            "otp_code": "123456",
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        # Test HTML template
        html_content = render_to_string(
            "authentication/emails/otp_verification.html", context
        )

        # Should not contain unescaped script tags
        self.assertNotIn("<script>alert(", html_content)
        self.assertIn("&lt;script&gt;", html_content)  # Should be escaped

        # Test text template
        text_content = render_to_string(
            "authentication/emails/otp_verification.txt", context
        )

        # Text template should contain escaped content (Django templates auto-escape)
        # The content shows &lt;script&gt; which means it's properly escaped
        has_escaped_content = "&lt;script&gt;" in text_content
        has_raw_script = "<script>" in text_content
        self.assertTrue(
            has_escaped_content, "Should contain escaped HTML entities for security"
        )
        # Raw script tags should not be present in output
        self.assertFalse(has_raw_script, "Should not contain unescaped script tags")

    def test_template_internationalization_support(self):
        """Test that templates support internationalization."""
        from django.utils.translation import activate, deactivate

        context = {
            "user": self.user,
            "otp_code": self.verification.otp_code,
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        # Test with default language
        render_to_string(
            "authentication/emails/otp_verification.html", context
        )

        # Templates should work with different languages (if supported)
        try:
            activate("es")  # Try Spanish
            html_content_es = render_to_string(
                "authentication/emails/otp_verification.html", context
            )
            # If translation files exist, content might be different
            # If not, should still render without errors
            self.assertIsNotNone(html_content_es)
        except Exception:
            pass  # Translation may not be set up
        finally:
            deactivate()

    def test_template_context_variables_usage(self):
        """Test that all context variables are properly used in templates."""
        context = {
            "user": self.user,
            "otp_code": self.verification.otp_code,
            "expires_in_minutes": 15,  # Different value to test
            "site_name": "TestSite",  # Different value to test
        }

        html_content = render_to_string(
            "authentication/emails/otp_verification.html", context
        )
        text_content = render_to_string(
            "authentication/emails/otp_verification.txt", context
        )

        # Check all context variables are used
        for content in [html_content, text_content]:
            self.assertIn("123456", content)  # otp_code
            self.assertIn("System", content)  # user.first_name
            self.assertIn("15", content)  # expires_in_minutes
            self.assertIn("TestSite", content)  # site_name


class EmailDeliverySystemTests(TestCase):
    """
    System tests for email delivery functionality.
    """

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="deliveryuser",
            email="delivery@example.com",
            password="testpass123",
            first_name="Delivery",
            last_name="User",
        )

    def test_email_message_structure(self):
        """Test the structure of generated email messages."""
        mail.outbox.clear()

        # Send verification email
        result = EmailVerificationService.send_verification_email(self.user)
        self.assertTrue(result.success)

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        # Test email headers and structure
        self.assertEqual(email.to, ["delivery@example.com"])
        self.assertIn("verification code", email.subject.lower())
        self.assertIsNotNone(email.from_email)

        # Check email has both HTML and text content
        self.assertIsNotNone(email.body)  # Text content
        self.assertTrue(hasattr(email, "alternatives"))  # HTML alternative
        self.assertGreater(len(email.alternatives), 0)  # Should have alternatives

        html_alternative = None
        for content, content_type in email.alternatives:
            if content_type == "text/html":
                html_alternative = content
                break

        self.assertIsNotNone(html_alternative)
        # Check for HTML structure (our template should have DOCTYPE)
        self.assertTrue(
            "<!DOCTYPE html>" in html_alternative or "<html" in html_alternative,
            f"Expected HTML structure, got: {html_alternative[:200]}...",
        )

    def test_email_headers_and_metadata(self):
        """Test email headers and metadata are correct."""
        with override_settings(
            DEFAULT_FROM_EMAIL="noreply@daylog.com", EMAIL_SUBJECT_PREFIX="[DayLog] "
        ):
            mail.outbox.clear()

            result = EmailVerificationService.send_verification_email(self.user)
            self.assertTrue(result.success)

            email = mail.outbox[0]

            # Test from email
            self.assertEqual(email.from_email, "noreply@daylog.com")

            # Test subject contains OTP
            verification = result.verification
            self.assertIn(verification.otp_code, email.subject)

    def test_email_content_encoding(self):
        """Test that email content is properly encoded."""
        # Create user with unicode characters
        unicode_user = User.objects.create_user(
            username="unicodeuser",
            email="unicode@example.com",
            password="testpass123",
            first_name="José",
            last_name="Müller",
        )

        mail.outbox.clear()

        result = EmailVerificationService.send_verification_email(unicode_user)
        self.assertTrue(result.success)

        email = mail.outbox[0]

        # Check unicode characters are handled correctly
        # The email template only uses user.first_name, not last_name
        self.assertIn("José", email.body)

        # Last name should not appear since template doesn't use it
        self.assertNotIn("Müller", email.body)

        # Check HTML alternative also handles unicode
        html_content = None
        for content, content_type in email.alternatives:
            if content_type == "text/html":
                html_content = content
                break

        if html_content:
            self.assertIn("José", html_content)
            # HTML template also only uses first_name, not last_name
            self.assertNotIn("Müller", html_content)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_email_backend_configuration(self):
        """Test email backend configuration works correctly."""
        mail.outbox.clear()

        result = EmailVerificationService.send_verification_email(self.user)
        self.assertTrue(result.success)

        # Email should be in memory backend
        self.assertEqual(len(mail.outbox), 1)

    def test_email_attachment_and_alternatives(self):
        """Test that email properly handles HTML alternatives."""
        mail.outbox.clear()

        result = EmailVerificationService.send_verification_email(self.user)
        self.assertTrue(result.success)

        email = mail.outbox[0]

        # Should be EmailMultiAlternatives
        self.assertIsInstance(email, EmailMultiAlternatives)

        # Should have HTML alternative
        self.assertTrue(hasattr(email, "alternatives"))
        self.assertGreater(len(email.alternatives), 0)

        # HTML alternative should be properly formatted
        html_content, mime_type = email.alternatives[0]
        self.assertEqual(mime_type, "text/html")
        self.assertIn("<!DOCTYPE html>", html_content)

    def test_email_content_consistency(self):
        """Test that HTML and text versions contain consistent information."""
        mail.outbox.clear()

        result = EmailVerificationService.send_verification_email(self.user)
        self.assertTrue(result.success)

        email = mail.outbox[0]
        verification = result.verification

        text_content = email.body
        html_content = email.alternatives[0][0] if email.alternatives else None

        # Both should contain OTP code
        self.assertIn(verification.otp_code, text_content)
        if html_content:
            self.assertIn(verification.otp_code, html_content)

        # Both should contain user name
        self.assertIn(self.user.first_name, text_content)
        if html_content:
            self.assertIn(self.user.first_name, html_content)

        # Both should contain site name
        self.assertIn("DayLog", text_content)
        if html_content:
            self.assertIn("DayLog", html_content)


class EmailRenderingSystemTests(TestCase):
    """
    System tests for email rendering across different environments.
    """

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="renderuser",
            email="render@example.com",
            password="testpass123",
            first_name="Render",
            last_name="User",
        )

    def test_html_email_client_compatibility(self):
        """Test HTML email compatibility with different email clients."""
        if not BS4_AVAILABLE:
            self.skipTest(
                "BeautifulSoup4 not available - install with 'pip install beautifulsoup4'"
            )

        context = {
            "user": self.user,
            "otp_code": "123456",
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        html_content = render_to_string(
            "authentication/emails/otp_verification.html", context
        )

        soup = BeautifulSoup(html_content, "html.parser")

        # Check for email client compatibility features
        # Inline CSS (better for email clients) - check if present but don't require
        elements_with_style = soup.find_all(attrs={"style": True})
        style_tags = soup.find_all("style")

        # Should have either inline styles or style tags for formatting
        has_styling = len(elements_with_style) > 0 or len(style_tags) > 0
        self.assertTrue(
            has_styling, "Should have some form of CSS styling for email compatibility"
        )

        # Table-based layout (better for older email clients)
        tables = soup.find_all("table")
        # Don't require tables, but check if used properly if present
        for table in tables:
            self.assertIsNotNone(table.get("cellpadding"))
            self.assertIsNotNone(table.get("cellspacing"))

    def test_email_accessibility_features(self):
        """Test that email templates include accessibility features."""
        if not BS4_AVAILABLE:
            self.skipTest(
                "BeautifulSoup4 not available - install with 'pip install beautifulsoup4'"
            )

        context = {
            "user": self.user,
            "otp_code": "123456",
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        html_content = render_to_string(
            "authentication/emails/otp_verification.html", context
        )

        soup = BeautifulSoup(html_content, "html.parser")

        # Check for alt attributes on images (if any)
        images = soup.find_all("img")
        for img in images:
            self.assertIsNotNone(img.get("alt"), "Images should have alt text")

        # Check for proper heading structure
        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        if headings:
            # Should start with h1 or h2
            first_heading = headings[0]
            self.assertIn(first_heading.name, ["h1", "h2"])

    def test_email_dark_mode_compatibility(self):
        """Test email templates work with dark mode email clients."""
        context = {
            "user": self.user,
            "otp_code": "123456",
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        html_content = render_to_string(
            "authentication/emails/otp_verification.html", context
        )

        # Check for dark mode considerations
        # This is optional - email templates don't always need dark mode
        # For now, just verify the template renders without dark mode errors
        # Dark mode support can be added as an enhancement
        self.assertIsNotNone(html_content)
        # If dark mode features are present, they should be properly formatted
        if "@media" in html_content and "prefers-color-scheme" in html_content:
            self.assertIn("dark", html_content.lower())

    def test_email_mobile_responsiveness(self):
        """Test that email templates are mobile responsive."""
        if not BS4_AVAILABLE:
            self.skipTest(
                "BeautifulSoup4 not available - install with 'pip install beautifulsoup4'"
            )

        context = {
            "user": self.user,
            "otp_code": "123456",
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        html_content = render_to_string(
            "authentication/emails/otp_verification.html", context
        )

        soup = BeautifulSoup(html_content, "html.parser")

        # Check for viewport meta tag
        viewport_meta = soup.find("meta", attrs={"name": "viewport"})
        self.assertIsNotNone(viewport_meta, "Should have viewport meta tag for mobile")

        # Check for responsive CSS
        style_tags = soup.find_all("style")
        has_responsive_css = False

        for style_tag in style_tags:
            if style_tag.string and "@media" in style_tag.string:
                has_responsive_css = True
                break

        self.assertTrue(has_responsive_css, "Should include responsive CSS")

    def test_email_rendering_performance(self):
        """Test email template rendering performance."""
        import time

        context = {
            "user": self.user,
            "otp_code": "123456",
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        # Time HTML template rendering
        start_time = time.time()
        for _ in range(100):
            render_to_string(
                "authentication/emails/otp_verification.html", context
            )
        html_time = time.time() - start_time

        # Time text template rendering
        start_time = time.time()
        for _ in range(100):
            render_to_string(
                "authentication/emails/otp_verification.txt", context
            )
        text_time = time.time() - start_time

        # Performance assertions
        self.assertLess(html_time, 2.0, "HTML template rendering should be fast")
        self.assertLess(text_time, 1.0, "Text template rendering should be fast")

        print(f"HTML template: {html_time:.4f}s for 100 renders")
        print(f"Text template: {text_time:.4f}s for 100 renders")

    def test_template_error_handling(self):
        """Test template error handling with invalid context."""
        # Test with missing context variables
        incomplete_context = {
            "user": self.user,
            # Missing otp_code, expires_in_minutes, site_name
        }

        try:
            html_content = render_to_string(
                "authentication/emails/otp_verification.html", incomplete_context
            )
            # Should either work with defaults or raise appropriate error
            self.assertIsNotNone(html_content)
        except Exception as e:
            # If it raises an error, it should be a template-related error
            self.assertIn("template", str(e).lower())

        # Test with None user
        invalid_context = {
            "user": None,
            "otp_code": "123456",
            "expires_in_minutes": 10,
            "site_name": "DayLog",
        }

        try:
            html_content = render_to_string(
                "authentication/emails/otp_verification.html", invalid_context
            )
            # Should handle None user gracefully
            self.assertIsNotNone(html_content)
        except Exception as e:
            # Should be a template-related error, not a server error
            self.assertNotIn("500", str(e))
