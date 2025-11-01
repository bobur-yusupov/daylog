from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from journal.models import Tag, JournalEntry

User = get_user_model()


class JournalAPITestCase(TestCase):
    """Test cases for Journal API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.client.force_authenticate(user=self.user)

        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "header-1",
                    "type": "header",
                    "data": {"text": "Test Journal Entry", "level": 2},
                },
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {"text": "This is a test journal entry content."},
                },
            ],
            "version": "2.28.2",
        }

    def test_create_tag(self):
        """Test creating a new tag"""
        url = reverse("api:tag-list")
        data = {"name": "Test Tag"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(Tag.objects.first().name, "test tag")  # Tag names are normalized to lowercase
        self.assertEqual(Tag.objects.first().user, self.user)

    def test_create_duplicate_tag(self):
        """Test that duplicate tags are rejected"""
        Tag.objects.create(user=self.user, name="Duplicate")

        url = reverse("api:tag-list")
        data = {"name": "Duplicate"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already exists", response.data["error"])

    def test_list_tags(self):
        """Test listing user tags"""
        Tag.objects.create(user=self.user, name="Tag1")
        Tag.objects.create(user=self.user, name="Tag2")

        # Create tag for another user (should not appear)
        other_user = User.objects.create_user(username="other", email="other@test.com")
        Tag.objects.create(user=other_user, name="OtherTag")

        url = reverse("api:tag-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_create_journal_entry(self):
        """Test creating a new journal entry"""
        url = reverse("api:journalentry-list")
        data = {
            "title": "Test Entry",
            "content": self.sample_content,
            "is_public": False,
            "tag_names": ["Tag1", "Tag2"],
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JournalEntry.objects.count(), 1)

        entry = JournalEntry.objects.first()
        self.assertEqual(entry.title, "Test Entry")
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.tags.count(), 2)

    def test_create_journal_entry_invalid_content(self):
        """Test creating journal entry with invalid EditorJS content"""
        url = reverse("api:journalentry-list")
        data = {
            "title": "Test Entry",
            "content": {"invalid": "content"},  # Missing blocks
            "is_public": False,
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_journal_entry_content_stats(self):
        """Test getting content statistics for journal entry"""
        entry = JournalEntry.objects.create(
            user=self.user, title="Test Entry", content=self.sample_content
        )

        url = reverse("api:journalentry-content-stats", kwargs={"pk": entry.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("block_count", response.data)
        self.assertEqual(response.data["block_count"], 2)

    def test_search_entries(self):
        """Test searching journal entries"""
        JournalEntry.objects.create(
            user=self.user, title="Python Programming", content=self.sample_content
        )
        JournalEntry.objects.create(
            user=self.user, title="Django Tutorial", content=self.sample_content
        )

        url = reverse("api:journalentry-search")
        response = self.client.get(url, {"q": "Python"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Python Programming")

    def test_duplicate_entry(self):
        """Test duplicating a journal entry"""
        original_entry = JournalEntry.objects.create(
            user=self.user, title="Original Entry", content=self.sample_content
        )
        tag = Tag.objects.create(user=self.user, name="TestTag")
        original_entry.tags.add(tag)

        url = reverse("api:journalentry-duplicate", kwargs={"pk": original_entry.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(JournalEntry.objects.count(), 2)

        new_entry = JournalEntry.objects.exclude(id=original_entry.id).first()
        self.assertTrue(new_entry.title.startswith("Copy of"))
        self.assertEqual(new_entry.tags.count(), 1)
        self.assertFalse(new_entry.is_public)  # Copies should always be private

    def test_tag_entries_endpoint(self):
        """Test getting entries for a specific tag"""
        tag = Tag.objects.create(user=self.user, name="TestTag")
        entry1 = JournalEntry.objects.create(
            user=self.user, title="Entry 1", content=self.sample_content
        )
        entry2 = JournalEntry.objects.create(
            user=self.user, title="Entry 2", content=self.sample_content
        )

        entry1.tags.add(tag)
        entry2.tags.add(tag)

        url = reverse("api:tag-entries", kwargs={"pk": tag.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if using pagination (results) or fallback (entries)
        if "results" in response.data:
            self.assertEqual(len(response.data["results"]), 2)
        else:
            self.assertEqual(len(response.data["entries"]), 2)
        self.assertEqual(response.data["count"], 2)

    def test_unauthorized_access(self):
        """Test that unauthenticated users cannot access the API"""
        self.client.force_authenticate(user=None)

        url = reverse("api:tag-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_pagination_tags(self):
        """Test pagination for tags list"""
        # Create more tags than the page size
        for i in range(25):
            Tag.objects.create(user=self.user, name=f"Tag {i:02d}")

        url = reverse("api:tag-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)
        self.assertIn("links", response.data)
        self.assertEqual(response.data["count"], 25)
        self.assertEqual(len(response.data["results"]), 20)  # Default page size
        self.assertIsNotNone(response.data["links"]["next"])

    def test_pagination_custom_page_size(self):
        """Test pagination with custom page size"""
        # Create entries
        for i in range(15):
            JournalEntry.objects.create(
                user=self.user, title=f"Entry {i:02d}", content=self.sample_content
            )

        url = reverse("api:journalentry-list")
        response = self.client.get(url, {"page_size": 5})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)
        self.assertEqual(response.data["page_size"], 5)
        self.assertEqual(response.data["total_pages"], 3)

    def test_pagination_search_results(self):
        """Test pagination for search results"""
        # Create entries with similar titles
        for i in range(30):
            JournalEntry.objects.create(
                user=self.user,
                title=f"Python Tutorial {i:02d}",
                content=self.sample_content,
            )

        url = reverse("api:journalentry-search")
        response = self.client.get(url, {"q": "Python"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertEqual(response.data["count"], 30)
        # Search uses LargePagination, so page size should be 50
        # But we only have 30 results, so all should be on first page
        self.assertEqual(len(response.data["results"]), 30)

    def test_filtered_entries_with_pagination(self):
        """Test filtered entries endpoint with pagination"""
        # Create entries with tags
        tag = Tag.objects.create(user=self.user, name="FilterTag")
        for i in range(25):
            entry = JournalEntry.objects.create(
                user=self.user, title=f"Entry {i:02d}", content=self.sample_content
            )
            if i % 2 == 0:  # Add tag to every other entry
                entry.tags.add(tag)

        url = reverse("api:journalentry-filtered")
        response = self.client.get(url, {"has_tags": "true"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertEqual(
            response.data["count"], 13
        )  # 13 entries have tags (0,2,4,...,24)
        self.assertEqual(len(response.data["results"]), 13)  # All fit on one page
