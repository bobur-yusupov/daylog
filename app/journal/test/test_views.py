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

    def test_dashboard_view_requires_login(self):
        """Test that dashboard view requires authentication"""
        url = reverse("journal:dashboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_dashboard_view_authenticated_access(self):
        """Test authenticated access to dashboard"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "testuser")
        self.assertTemplateUsed(response, "journal/dashboard.html")

    def test_dashboard_context_data(self):
        """Test that dashboard provides correct context data"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard")
        response = self.client.get(url)

        context = response.context
        self.assertEqual(context["user"], self.user)
        self.assertEqual(len(context["recent_entries"]), 2)
        self.assertEqual(len(context["recent_tags"]), 3)
        self.assertEqual(context["total_entries"], 2)
        self.assertEqual(context["total_tags"], 3)

        # Check that entries are ordered by most recent first
        entries = list(context["recent_entries"])
        self.assertEqual(entries[0], self.entry2)  # Most recent
        self.assertEqual(entries[1], self.entry1)

    def test_dashboard_only_shows_user_data(self):
        """Test that dashboard only shows data for current user"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard")
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
        response = self.client.get(url)

        context = response.context
        self.assertEqual(len(context["recent_entries"]), 5)
        self.assertEqual(context["total_entries"], 9)

    def test_dashboard_limits_recent_tags(self):
        """Test that dashboard limits recent tags to 10"""
        # Create 12 more tags (total 15)
        for i in range(12):
            Tag.objects.create(user=self.user, name=f"Tag {i + 4}")

        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:dashboard")
        response = self.client.get(url)

        context = response.context
        self.assertEqual(len(context["recent_tags"]), 10)
        self.assertEqual(context["total_tags"], 15)


class JournalListViewTests(BaseViewTestCase):
    """Tests for the JournalListView"""

    def test_journal_list_requires_login(self):
        """Test that journal list view requires authentication"""
        url = reverse("journal:entry_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_journal_list_authenticated_access(self):
        """Test authenticated access to journal list"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/entry_list.html")

    def test_journal_list_context_data(self):
        """Test that journal list provides correct context data"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_list")
        response = self.client.get(url)

        context = response.context
        self.assertEqual(len(context["entries"]), 2)
        self.assertEqual(len(context["tags"]), 3)
        self.assertIsNone(context["current_tag"])
        self.assertIsNone(context["search_query"])

    def test_journal_list_tag_filtering(self):
        """Test filtering journal entries by tag"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_list")
        response = self.client.get(url, {"tag": "Personal"})

        context = response.context
        self.assertEqual(len(context["entries"]), 1)
        self.assertEqual(context["entries"].first(), self.entry1)
        self.assertEqual(context["current_tag"], "Personal")

    def test_journal_list_search_functionality(self):
        """Test search functionality in journal list"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_list")
        response = self.client.get(url, {"search": "Entry 1"})

        context = response.context
        self.assertEqual(len(context["entries"]), 1)
        self.assertEqual(context["entries"].first(), self.entry1)
        self.assertEqual(context["search_query"], "Entry 1")

    def test_journal_list_combined_filtering(self):
        """Test combined tag filtering and search"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_list")
        response = self.client.get(url, {"tag": "Work", "search": "Entry 2"})

        context = response.context
        self.assertEqual(len(context["entries"]), 1)
        self.assertEqual(context["entries"].first(), self.entry2)

    def test_journal_list_no_results(self):
        """Test journal list when no entries match criteria"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_list")
        response = self.client.get(url, {"search": "NonExistent"})

        context = response.context
        self.assertEqual(len(context["entries"]), 0)

    def test_journal_list_only_user_entries(self):
        """Test that journal list only shows current user's entries"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_list")
        response = self.client.get(url)

        context = response.context
        entry_ids = [entry.id for entry in context["entries"]]
        self.assertNotIn(self.other_entry.id, entry_ids)

        # Check tags are also user-specific
        tag_names = [tag.name for tag in context["tags"]]
        self.assertIn("Personal", tag_names)
        self.assertIn("Work", tag_names)
        self.assertIn("Ideas", tag_names)


class JournalDetailViewTests(BaseViewTestCase):
    """Tests for the JournalDetailView"""

    def test_journal_detail_requires_login(self):
        """Test that journal detail view requires authentication"""
        url = reverse("journal:entry_detail", kwargs={"entry_id": self.entry1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_journal_detail_authenticated_access(self):
        """Test authenticated access to journal detail"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_detail", kwargs={"entry_id": self.entry1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/entry_detail.html")

    def test_journal_detail_context_data(self):
        """Test that journal detail provides correct context data"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_detail", kwargs={"entry_id": self.entry1.id})
        response = self.client.get(url)

        context = response.context
        self.assertEqual(context["entry"], self.entry1)

    def test_journal_detail_user_ownership_check(self):
        """Test that users can only view their own entries"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_detail", kwargs={"entry_id": self.other_entry.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_journal_detail_nonexistent_entry(self):
        """Test accessing nonexistent journal entry"""
        from uuid import uuid4

        fake_id = uuid4()

        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:entry_detail", kwargs={"entry_id": fake_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)


class NewJournalViewTests(BaseViewTestCase):
    """Tests for the NewJournalView"""

    def test_new_journal_requires_login(self):
        """Test that new journal view requires authentication"""
        url = reverse("journal:new_entry")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_new_journal_get_request(self):
        """Test GET request to new journal view"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:new_entry")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/entry_create.html")

        context = response.context
        self.assertEqual(len(context["available_tags"]), 3)

    def test_new_journal_successful_post(self):
        """Test successful journal entry creation"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:new_entry")

        data = {
            "title": "New Test Entry",
            "content": json.dumps(self.sample_content),
            "is_public": "on",
            "tags": ["Personal", "NewTag"],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("journal:dashboard"))

        # Check that entry was created
        entry = JournalEntry.objects.get(title="New Test Entry")
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.content, self.sample_content)
        self.assertTrue(entry.is_public)
        self.assertEqual(entry.tags.count(), 2)

        # Check that new tag was created
        self.assertTrue(Tag.objects.filter(name="NewTag", user=self.user).exists())

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn("created successfully", str(messages[0]))

    def test_new_journal_missing_title(self):
        """Test journal creation with missing title"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:new_entry")

        data = {
            "title": "",
            "content": json.dumps(self.sample_content),
            "tags": ["Personal"],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)  # Returns to form
        self.assertContains(response, "Title is required")

        # Check that entry was not created
        self.assertFalse(JournalEntry.objects.filter(title="").exists())

    def test_new_journal_missing_content(self):
        """Test journal creation with missing content"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:new_entry")

        data = {"title": "Test Entry", "content": "", "tags": ["Personal"]}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)  # Returns to form
        self.assertContains(response, "Content is required")

    def test_new_journal_invalid_json_content(self):
        """Test journal creation with invalid JSON content"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:new_entry")

        data = {
            "title": "Test Entry",
            "content": "invalid json content",
            "tags": ["Personal"],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)  # Returns to form
        self.assertContains(response, "Invalid content format")

    def test_new_journal_is_public_false(self):
        """Test journal creation with is_public=False"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:new_entry")

        data = {
            "title": "Private Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["Personal"],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        entry = JournalEntry.objects.get(title="Private Entry")
        self.assertFalse(entry.is_public)

    def test_new_journal_empty_tags(self):
        """Test journal creation with empty/whitespace tags"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:new_entry")

        data = {
            "title": "Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["Valid Tag", "", "   ", "Another Valid"],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        entry = JournalEntry.objects.get(title="Test Entry")
        self.assertEqual(entry.tags.count(), 2)  # Only valid tags

        tag_names = [tag.name for tag in entry.tags.all()]
        self.assertIn("Valid Tag", tag_names)
        self.assertIn("Another Valid", tag_names)

    def test_new_journal_exception_handling(self):
        """Test exception handling during journal creation"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:new_entry")

        with patch(
            "journal.views.create_views.JournalEntry.objects.create"
        ) as mock_create:
            mock_create.side_effect = Exception("Database error")

            data = {
                "title": "Test Entry",
                "content": json.dumps(self.sample_content),
                "tags": ["Personal"],
            }

            response = self.client.post(url, data)

            self.assertEqual(response.status_code, 200)  # Returns to form
            messages = list(get_messages(response.wsgi_request))
            self.assertTrue(
                any("Error creating journal entry" in str(msg) for msg in messages)
            )


class EditJournalViewTests(BaseViewTestCase):
    """Tests for the EditJournalView"""

    def test_edit_journal_requires_login(self):
        """Test that edit journal view requires authentication"""
        url = reverse("journal:edit_entry", kwargs={"entry_id": self.entry1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_edit_journal_get_request(self):
        """Test GET request to edit journal view"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": self.entry1.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "journal/entry_edit.html")

        context = response.context
        self.assertEqual(context["entry"], self.entry1)
        self.assertEqual(len(context["available_tags"]), 3)
        self.assertIn("content_data", context)

    def test_edit_journal_user_ownership_check(self):
        """Test that users can only edit their own entries"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": self.other_entry.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_edit_journal_successful_post(self):
        """Test successful journal entry update"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": self.entry1.id})

        updated_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {"text": "Updated content for the journal entry."},
                }
            ],
            "version": "2.28.2",
        }

        data = {
            "title": "Updated Test Entry",
            "content": json.dumps(updated_content),
            "is_public": "on",
            "tags": ["Work", "Updated"],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("journal:entry_detail", kwargs={"entry_id": self.entry1.id}),
        )

        # Check that entry was updated
        entry = JournalEntry.objects.get(id=self.entry1.id)
        self.assertEqual(entry.title, "Updated Test Entry")
        self.assertEqual(entry.content, updated_content)
        self.assertTrue(entry.is_public)
        self.assertEqual(entry.tags.count(), 2)

        # Check that tags were updated
        tag_names = [tag.name for tag in entry.tags.all()]
        self.assertIn("Work", tag_names)
        self.assertIn("Updated", tag_names)
        self.assertNotIn("Personal", tag_names)  # Should be removed

        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("updated successfully" in str(msg) for msg in messages))

    def test_edit_journal_missing_title(self):
        """Test journal update with missing title"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": self.entry1.id})

        data = {
            "title": "",
            "content": json.dumps(self.sample_content),
            "tags": ["Personal"],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Title is required" in str(msg) for msg in messages))

    def test_edit_journal_missing_content(self):
        """Test journal update with missing content"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": self.entry1.id})

        data = {"title": "Updated Entry", "content": "", "tags": ["Personal"]}

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Content is required" in str(msg) for msg in messages))

    def test_edit_journal_invalid_json_content(self):
        """Test journal update with invalid JSON content"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": self.entry1.id})

        data = {
            "title": "Updated Entry",
            "content": "invalid json",
            "tags": ["Personal"],
        }

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)

        # Check error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid content format" in str(msg) for msg in messages))

    def test_edit_journal_content_handling_edge_cases(self):
        """Test handling of edge cases in content"""
        # Create entry with empty dict content (valid JSON)
        entry = JournalEntry.objects.create(
            user=self.user, title="Empty Content Entry", content={}
        )

        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": entry.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        # Should handle None content gracefully
        self.assertIn("content_data", response.context)

    def test_edit_journal_nonexistent_entry(self):
        """Test editing nonexistent journal entry"""
        from uuid import uuid4

        fake_id = uuid4()

        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": fake_id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_edit_journal_exception_handling(self):
        """Test exception handling during journal update"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:edit_entry", kwargs={"entry_id": self.entry1.id})

        # Test with invalid JSON content to trigger validation error
        data = {
            "title": "Updated Entry",
            "content": "invalid json content",  # This should cause validation error
            "tags": ["Personal"],
        }

        response = self.client.post(url, data)

        # Should redirect back to edit form on error
        self.assertEqual(response.status_code, 302)
        expected_url = reverse(
            "journal:edit_entry", kwargs={"entry_id": self.entry1.id}
        )
        self.assertRedirects(response, expected_url)

        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid content format" in str(msg) for msg in messages))


class TagAutocompleteViewTests(BaseViewTestCase):
    """Tests for the TagAutocompleteView"""

    def test_tag_autocomplete_requires_login(self):
        """Test that tag autocomplete view requires authentication"""
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_tag_autocomplete_successful_request(self):
        """Test successful tag autocomplete request"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url, {"q": "Per"})

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, JsonResponse)

        data = json.loads(response.content)
        self.assertIn("tags", data)
        self.assertIn("Personal", data["tags"])

    def test_tag_autocomplete_empty_query(self):
        """Test tag autocomplete with empty query"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url, {"q": ""})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["tags"], [])

    def test_tag_autocomplete_no_query_parameter(self):
        """Test tag autocomplete without query parameter"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["tags"], [])

    def test_tag_autocomplete_case_insensitive(self):
        """Test that tag autocomplete is case insensitive"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url, {"q": "work"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("Work", data["tags"])

    def test_tag_autocomplete_partial_match(self):
        """Test tag autocomplete with partial matches"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url, {"q": "ide"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("Ideas", data["tags"])

    def test_tag_autocomplete_user_specific(self):
        """Test that tag autocomplete only returns current user's tags"""
        # Create tag for other user
        Tag.objects.create(user=self.other_user, name="OtherTag")

        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url, {"q": "Other"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertNotIn("OtherTag", data["tags"])

    def test_tag_autocomplete_limit(self):
        """Test that tag autocomplete limits results to 10"""
        # Create 15 tags that match the query
        for i in range(15):
            Tag.objects.create(user=self.user, name=f"Test{i}")

        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url, {"q": "Test"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data["tags"]), 10)

    def test_tag_autocomplete_post_request(self):
        """Test that POST request works for tag autocomplete (CSRF exempt)"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("journal:tag_autocomplete")
        response = self.client.post(url, {"q": "Personal"})

        # Should return empty response for POST as view only handles GET
        self.assertEqual(response.status_code, 405)  # Method not allowed


class JournalViewIntegrationTests(BaseViewTestCase):
    """Integration tests for journal views working together"""

    def test_complete_journal_workflow(self):
        """Test complete workflow from creation to viewing to editing"""
        self.client.login(username="testuser", password="testpass123")

        # Step 1: Create new journal entry
        create_url = reverse("journal:new_entry")
        create_data = {
            "title": "Workflow Test Entry",
            "content": json.dumps(self.sample_content),
            "is_public": "on",
            "tags": ["Workflow", "Test"],
        }

        create_response = self.client.post(create_url, create_data)
        self.assertEqual(create_response.status_code, 302)

        # Get the created entry
        entry = JournalEntry.objects.get(title="Workflow Test Entry")

        # Step 2: View the entry detail
        detail_url = reverse("journal:entry_detail", kwargs={"entry_id": entry.id})
        detail_response = self.client.get(detail_url)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Workflow Test Entry")

        # Step 3: Edit the entry
        edit_url = reverse("journal:edit_entry", kwargs={"entry_id": entry.id})
        edit_data = {
            "title": "Updated Workflow Test Entry",
            "content": json.dumps(self.sample_content),
            "is_public": "",  # Make it private
            "tags": ["Workflow", "Updated"],
        }

        edit_response = self.client.post(edit_url, edit_data)
        self.assertEqual(edit_response.status_code, 302)

        # Step 4: Verify changes in detail view
        detail_response2 = self.client.get(detail_url)
        self.assertEqual(detail_response2.status_code, 200)
        self.assertContains(detail_response2, "Updated Workflow Test Entry")

        # Verify entry was updated
        entry.refresh_from_db()
        self.assertEqual(entry.title, "Updated Workflow Test Entry")
        self.assertFalse(entry.is_public)
        self.assertEqual(entry.tags.count(), 2)

    def test_dashboard_reflects_new_entries(self):
        """Test that dashboard reflects newly created entries"""
        self.client.login(username="testuser", password="testpass123")

        # Check initial dashboard state
        dashboard_url = reverse("journal:dashboard")
        initial_response = self.client.get(dashboard_url)
        initial_count = initial_response.context["total_entries"]

        # Create new entry
        create_url = reverse("journal:new_entry")
        create_data = {
            "title": "Dashboard Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["Dashboard"],
        }

        self.client.post(create_url, create_data)

        # Check dashboard reflects new entry
        final_response = self.client.get(dashboard_url)
        final_count = final_response.context["total_entries"]

        self.assertEqual(final_count, initial_count + 1)
        self.assertContains(final_response, "Dashboard Test Entry")

    def test_list_view_reflects_filtering(self):
        """Test that list view properly reflects filtering and searching"""
        self.client.login(username="testuser", password="testpass123")

        # Create entries with specific tags and titles
        for i in range(3):
            entry = JournalEntry.objects.create(
                user=self.user,
                title=f"Filter Test Entry {i}",
                content=self.sample_content,
            )
            if i % 2 == 0:
                entry.tags.add(self.tag1)  # Personal

        list_url = reverse("journal:entry_list")

        # Test tag filtering
        filtered_response = self.client.get(list_url, {"tag": "Personal"})
        filtered_entries = list(filtered_response.context["entries"])

        # Should include original entry1 plus new even-numbered entries
        expected_count = 3  # entry1 + 2 new entries with Personal tag
        self.assertEqual(len(filtered_entries), expected_count)

        # Test search functionality
        search_response = self.client.get(list_url, {"search": "Filter Test"})
        search_entries = list(search_response.context["entries"])

        self.assertEqual(len(search_entries), 3)  # All 3 new entries match

        # Test combined filtering
        combined_response = self.client.get(
            list_url, {"tag": "Personal", "search": "Filter Test"}
        )
        combined_entries = list(combined_response.context["entries"])

        self.assertEqual(len(combined_entries), 2)  # Only even-numbered entries
