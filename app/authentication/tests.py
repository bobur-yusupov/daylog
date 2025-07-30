from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthenticationTests(TestCase):
    """
    Test cases for user authentication views.
    """

    def test_register_view_get(self):
        """
        Test the registration view GET request.
        """
        response = self.client.get('/auth/register/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/register.html')
        self.assertContains(response, 'username')
        self.assertContains(response, 'email')
        self.assertContains(response, 'first_name')
        self.assertContains(response, 'last_name')

    def test_register_view_valid_data(self):
        """
        Test the registration view with valid form data.
        """
        # Test valid registration with all required fields
        response = self.client.post('/auth/register/', {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'ComplexPassword123!',
            'password2': 'ComplexPassword123!',
            'honeypot': '',  # Empty honeypot field
        })
        
        # Should redirect to login page after successful registration
        self.assertRedirects(response, '/auth/login/')
        
        # Check that user was actually created
        self.assertTrue(User.objects.filter(username='testuser').exists())
        user = User.objects.get(username='testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')

    def test_register_view_missing_required_fields(self):
        """
        Test the registration view with missing required fields.
        """
        # Test with missing username
        response = self.client.post('/auth/register/', {
            'username': '',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'ComplexPassword123!',
            'password2': 'ComplexPassword123!',
        })
        self.assertEqual(response.status_code, 200)  # Form should have errors
        self.assertContains(response, 'This field is required.')
        self.assertFalse(User.objects.filter(email='test@example.com').exists())

    def test_register_view_missing_email(self):
        """
        Test the registration view with missing email.
        """
        response = self.client.post('/auth/register/', {
            'username': 'testuser',
            'email': '',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'ComplexPassword123!',
            'password2': 'ComplexPassword123!',
        })
        self.assertEqual(response.status_code, 200)  # Form should have errors
        self.assertContains(response, 'This field is required.')
        self.assertFalse(User.objects.filter(username='testuser').exists())

    def test_register_view_duplicate_email(self):
        """
        Test registration with duplicate email.
        """
        # Create a user first
        User.objects.create_user(
            username='existinguser',
            email='test@example.com',
            first_name='Existing',
            last_name='User'
        )
        
        # Try to register with same email
        response = self.client.post('/auth/register/', {
            'username': 'newuser',
            'email': 'test@example.com',
            'first_name': 'New',
            'last_name': 'User',
            'password1': 'ComplexPassword123!',
            'password2': 'ComplexPassword123!',
        })
        self.assertEqual(response.status_code, 200)  # Form should have errors
        self.assertContains(response, 'A user with that email already exists.')
        # Ensure no new user was created
        self.assertEqual(User.objects.filter(email='test@example.com').count(), 1)

    def test_register_view_honeypot_protection(self):
        """
        Test that honeypot field prevents spam submissions.
        """
        response = self.client.post('/auth/register/', {
            'username': 'spammer',
            'email': 'spam@example.com',
            'first_name': 'Spam',
            'last_name': 'Bot',
            'password1': 'ComplexPassword123!',
            'password2': 'ComplexPassword123!',
            'honeypot': 'spam content',  # Bot filled honeypot
        })
        self.assertEqual(response.status_code, 200)  # Form should have errors
        # Check for the message that's added by the view, not the form error
        messages = list(response.context['messages'])
        self.assertTrue(any('Detected spam submission.' in str(message) for message in messages))
        self.assertFalse(User.objects.filter(username='spammer').exists())

    def test_register_view_password_mismatch(self):
        """
        Test registration with mismatched passwords.
        """
        response = self.client.post('/auth/register/', {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'ComplexPassword123!',
            'password2': 'DifferentPassword456!',
        })
        self.assertEqual(response.status_code, 200)  # Form should have errors
        # Check that the form has errors and the user was not created
        # Password mismatch errors are handled by Django's UserCreationForm
        self.assertContains(response, "password")  # Look for any password-related error
        self.assertFalse(User.objects.filter(username='testuser').exists())
