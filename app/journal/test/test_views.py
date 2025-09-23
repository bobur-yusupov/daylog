import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.http import JsonResponse
from unittest.mock import patch

from journal.models import Tag, JournalEntry

User = get_user_model()


class BaseViewTestCase(TestCase):
    """Base test case with common setup for all view tests"""

    def setUp(self):
        """Set up test data for all view tests"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

        # Create some test tags
        self.tag1 = Tag.objects.create(user=self.user, name="Personal")
        self.tag2 = Tag.objects.create(user=self.user, name="Work")
        self.tag3 = Tag.objects.create(user=self.user, name="Ideas")

        # Sample EditorJS content
        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {"text": "This is a test journal entry content."},
                }
            ],
            "version": "2.28.2",
        }

        # Create some test journal entries
        self.entry1 = JournalEntry.objects.create(
            user=self.user,
            title="Test Entry 1",
            content=self.sample_content,
            is_public=False,
        )
        self.entry1.tags.add(self.tag1, self.tag2)

        self.entry2 = JournalEntry.objects.create(
            user=self.user,
            title="Test Entry 2",
            content=self.sample_content,
            is_public=True,
        )
        self.entry2.tags.add(self.tag2, self.tag3)

        # Create entry for other user
        self.other_entry = JournalEntry.objects.create(
            user=self.other_user,
            title="Other User Entry",
            content=self.sample_content,
            is_public=False,
        )


class DashboardViewTests(BaseViewTestCase):
    """Tests for the DashboardView"""
    def setUp(self):
        super().setUp()
        self.journalEntry = JournalEntry.objects.create(
            user=self.user, title="Sample Entry", content=self.sample_content
        )

    def test_dashboard_view_requires_login(self):
        """Test that dashboard view requires authentication"""
        url = reverse("journal:dashboard_with_entry", kwargs={"entry_id": self.journalEntry.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_dashboard_view_authenticated_access(self):
        """Test authenticated access to dashboard"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard_with_entry", kwargs={"entry_id": self.journalEntry.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/dashboard.html")

    def test_dashboard_context_data(self):
        """Test that dashboard provides correct context data"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard")
        response = self.client.get(url, follow=True)

        context = response.context
        self.assertEqual(context["user"], self.user)
        self.assertEqual(len(context["recent_entries"]), 3)  # Base 2 + 1 additional
        self.assertEqual(len(context["recent_tags"]), 3)
        self.assertEqual(context["total_entries"], 3)  # Base 2 + 1 additional
        self.assertEqual(context["total_tags"], 3)

        # Check that entries are ordered by most recent first
        entries = list(context["recent_entries"])
        self.assertEqual(entries[0], self.journalEntry)  # Most recent (created in DashboardViewTests.setUp)
        self.assertEqual(entries[1], self.entry2)  # Second most recent
        self.assertEqual(entries[2], self.entry1)  # Oldest

    def test_dashboard_only_shows_user_data(self):
        """Test that dashboard only shows data for current user"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard_with_entry", kwargs={"entry_id": self.entry1.id})
        response = self.client.get(url)

        context = response.context
        # Should not include other user's entry
        entry_ids = [entry.id for entry in context["recent_entries"]]
        self.assertNotIn(self.other_entry.id, entry_ids)

    def test_dashboard_limits_recent_entries(self):
        """Test that dashboard limits recent entries to 5"""
        # Create 7 more entries (total 9)
        for i in range(7):
            JournalEntry.objects.create(
                user=self.user, title=f"Entry {i + 3}", content=self.sample_content
            )

        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard")
        response = self.client.get(url, follow=True)

        context = response.context
        self.assertEqual(len(context["recent_entries"]), 5)
        self.assertEqual(context["total_entries"], 10)  # Base 2 + 1 additional + 7 new = 10

    def test_dashboard_limits_recent_tags(self):
        """Test that dashboard limits recent tags to 10"""
        # Create 12 more tags (total 15)
        for i in range(12):
            Tag.objects.create(user=self.user, name=f"Tag {i + 4}")

        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard")
        response = self.client.get(url, follow=True)

        context = response.context
        self.assertEqual(len(context["recent_tags"]), 10)
        self.assertEqual(context["total_tags"], 15)


