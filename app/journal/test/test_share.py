from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from journal.models import JournalEntry

User = get_user_model()


class ShareJournalTests(TestCase):
    """Tests for journal sharing functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )
        self.entry = JournalEntry.objects.create(
            user=self.user,
            title="Test Entry",
            content={"blocks": [{"type": "paragraph", "data": {"text": "Test content"}}]},
        )

    def test_generate_share_token(self):
        """Test generating a share token"""
        self.client.login(username="testuser", password="testpass123")

        url = reverse("journal:generate_share_token", kwargs={"entry_id": self.entry.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("share_token", data)
        self.assertIn("share_url", data)

        # Verify token was saved
        self.entry.refresh_from_db()
        self.assertIsNotNone(self.entry.share_token)
        self.assertEqual(self.entry.share_token, data["share_token"])

    def test_generate_share_token_requires_auth(self):
        """Test that generating share token requires authentication"""
        url = reverse("journal:generate_share_token", kwargs={"entry_id": self.entry.id})
        response = self.client.post(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_generate_share_token_requires_ownership(self):
        """Test that user can only generate token for their own entries"""
        self.client.login(username="otheruser", password="testpass123")

        url = reverse("journal:generate_share_token", kwargs={"entry_id": self.entry.id})
        response = self.client.post(url)

        # Should return 404 since entry doesn't belong to this user
        self.assertEqual(response.status_code, 404)

    def test_view_shared_entry(self):
        """Test viewing a shared entry without authentication"""
        # Generate share token
        token = self.entry.generate_share_token()

        # Access shared entry without logging in
        url = reverse("shared_entry", kwargs={"share_token": token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.entry.title)
        self.assertContains(response, "Shared Entry")
        self.assertContains(response, "Read-only view")

    def test_shared_entry_not_found(self):
        """Test accessing shared entry with invalid token"""
        url = reverse("shared_entry", kwargs={"share_token": "invalid-token"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_revoke_share_token(self):
        """Test revoking a share token"""
        # Generate token first
        self.entry.generate_share_token()
        self.assertIsNotNone(self.entry.share_token)

        # Login and revoke
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:revoke_share_token", kwargs={"entry_id": self.entry.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

        # Verify token was removed
        self.entry.refresh_from_db()
        self.assertIsNone(self.entry.share_token)

    def test_revoke_share_token_requires_auth(self):
        """Test that revoking share token requires authentication"""
        self.entry.generate_share_token()

        url = reverse("journal:revoke_share_token", kwargs={"entry_id": self.entry.id})
        response = self.client.post(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_revoke_share_token_requires_ownership(self):
        """Test that user can only revoke token for their own entries"""
        self.entry.generate_share_token()
        self.client.login(username="otheruser", password="testpass123")

        url = reverse("journal:revoke_share_token", kwargs={"entry_id": self.entry.id})
        response = self.client.post(url)

        # Should return 404 since entry doesn't belong to this user
        self.assertEqual(response.status_code, 404)

    def test_share_token_uniqueness(self):
        """Test that share tokens are unique"""
        entry2 = JournalEntry.objects.create(
            user=self.user,
            title="Another Entry",
            content={"blocks": []},
        )

        token1 = self.entry.generate_share_token()
        token2 = entry2.generate_share_token()

        self.assertNotEqual(token1, token2)

    def test_generate_token_idempotent(self):
        """Test that generating token multiple times returns same token"""
        token1 = self.entry.generate_share_token()
        token2 = self.entry.generate_share_token()

        self.assertEqual(token1, token2)
