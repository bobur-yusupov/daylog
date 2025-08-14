import json
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import IntegrityError
from django.utils import timezone
from unittest.mock import patch
import time

from journal.models import Tag, JournalEntry

User = get_user_model()


class JournalModelViewIntegrationTests(TestCase):
    """Integration tests between models and views"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

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

    def test_model_constraints_enforced_through_views(self):
        """Test that model constraints are properly enforced through view operations"""
        self.client.login(username="testuser", password="testpass123")

        # Test unique tag constraint through view
        Tag.objects.create(user=self.user, name="UniqueTag")

        # Try to create another entry with the same tag name (should reuse existing tag)
        url = reverse("journal:new_entry")
        data = {
            "title": "Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["UniqueTag"],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Should only have one tag with this name
        self.assertEqual(Tag.objects.filter(name="UniqueTag").count(), 1)

    def test_cascade_deletion_through_views(self):
        """Test cascade deletion behavior through view operations"""
        self.client.login(username="testuser", password="testpass123")

        # Create entry with tags
        entry = JournalEntry.objects.create(
            user=self.user, title="Test Entry", content=self.sample_content
        )
        tag = Tag.objects.create(user=self.user, name="TestTag")
        entry.tags.add(tag)

        entry_id = entry.id
        tag_id = tag.id

        # Delete user (should cascade delete entries and tags)
        self.user.delete()

        # Verify cascade deletion
        self.assertFalse(JournalEntry.objects.filter(id=entry_id).exists())
        self.assertFalse(Tag.objects.filter(id=tag_id).exists())

    def test_model_validation_through_view_operations(self):
        """Test that model validation is properly handled in views"""
        self.client.login(username="testuser", password="testpass123")

        # Test creating entry with title that exceeds max_length
        url = reverse("journal:new_entry")
        data = {
            "title": "x" * 300,  # Exceeds 255 char limit
            "content": json.dumps(self.sample_content),
            "tags": ["Test"],
        }

        response = self.client.post(url, data)

        # Should handle validation error gracefully
        # Implementation-dependent: might truncate, show error, or handle differently
        self.assertIn(response.status_code, [200, 302])

    def test_timestamp_behavior_through_views(self):
        """Test that model timestamps are properly maintained through view operations"""
        self.client.login(username="testuser", password="testpass123")

        # Create entry
        url = reverse("journal:new_entry")
        data = {
            "title": "Timestamp Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["Timestamp"],
        }

        create_time = timezone.now()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        entry = JournalEntry.objects.get(title="Timestamp Test Entry")

        # Verify creation timestamps
        self.assertGreaterEqual(entry.created_at, create_time)
        self.assertGreaterEqual(entry.updated_at, create_time)
        # Allow small time difference (within 1 second)
        time_diff = abs((entry.created_at - entry.updated_at).total_seconds())
        self.assertLess(time_diff, 1.0)

        # Wait a bit and update entry
        time.sleep(0.1)
        edit_url = reverse("journal:edit_entry", kwargs={"entry_id": entry.id})
        edit_data = {
            "title": "Updated Timestamp Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["Updated"],
        }

        update_time = timezone.now()
        edit_response = self.client.post(edit_url, edit_data)
        self.assertEqual(edit_response.status_code, 302)

        entry.refresh_from_db()

        # Verify update timestamps
        self.assertGreater(entry.updated_at, entry.created_at)
        self.assertGreaterEqual(entry.updated_at, update_time)


class JournalTagRelationshipIntegrationTests(TestCase):
    """Integration tests for journal entry and tag relationships"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {"text": "Test content"},
                }
            ],
            "version": "2.28.2",
        }

    def test_tag_creation_and_assignment_through_views(self):
        """Test creating and assigning tags through view operations"""
        self.client.login(username="testuser", password="testpass123")

        # Create entry with new and existing tags
        Tag.objects.create(user=self.user, name="ExistingTag")

        url = reverse("journal:new_entry")
        data = {
            "title": "Tag Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["ExistingTag", "NewTag1", "NewTag2"],
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Verify entry and tag relationships
        entry = JournalEntry.objects.get(title="Tag Test Entry")
        self.assertEqual(entry.tags.count(), 3)

        # Verify tags exist and are properly associated
        tag_names = [tag.name for tag in entry.tags.all()]
        self.assertIn("ExistingTag", tag_names)
        self.assertIn("NewTag1", tag_names)
        self.assertIn("NewTag2", tag_names)

        # Verify new tags were created for the user
        self.assertTrue(Tag.objects.filter(user=self.user, name="NewTag1").exists())
        self.assertTrue(Tag.objects.filter(user=self.user, name="NewTag2").exists())

    def test_tag_modification_through_edit_view(self):
        """Test modifying tags through edit view operations"""
        self.client.login(username="testuser", password="testpass123")

        # Create entry with initial tags
        entry = JournalEntry.objects.create(
            user=self.user, title="Tag Modification Test", content=self.sample_content
        )
        tag1 = Tag.objects.create(user=self.user, name="InitialTag1")
        tag2 = Tag.objects.create(user=self.user, name="InitialTag2")
        entry.tags.add(tag1, tag2)

        # Edit entry to change tags
        url = reverse("journal:edit_entry", kwargs={"entry_id": entry.id})
        data = {
            "title": "Tag Modification Test",
            "content": json.dumps(self.sample_content),
            "tags": [
                "InitialTag1",
                "NewTag3",
                "NewTag4",
            ],  # Remove InitialTag2, add new tags
        }

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Verify tag relationships were updated
        entry.refresh_from_db()
        self.assertEqual(entry.tags.count(), 3)

        tag_names = [tag.name for tag in entry.tags.all()]
        self.assertIn("InitialTag1", tag_names)
        self.assertIn("NewTag3", tag_names)
        self.assertIn("NewTag4", tag_names)
        self.assertNotIn("InitialTag2", tag_names)

        # Verify InitialTag2 still exists (not deleted, just removed from entry)
        self.assertTrue(Tag.objects.filter(name="InitialTag2").exists())

    def test_tag_filtering_in_list_view(self):
        """Test tag filtering functionality in list view"""
        self.client.login(username="testuser", password="testpass123")

        # Create entries with different tags
        tag1 = Tag.objects.create(user=self.user, name="FilterTag1")
        tag2 = Tag.objects.create(user=self.user, name="FilterTag2")

        entry1 = JournalEntry.objects.create(
            user=self.user, title="Entry with FilterTag1", content=self.sample_content
        )
        entry1.tags.add(tag1)

        entry2 = JournalEntry.objects.create(
            user=self.user, title="Entry with FilterTag2", content=self.sample_content
        )
        entry2.tags.add(tag2)

        entry3 = JournalEntry.objects.create(
            user=self.user, title="Entry with both tags", content=self.sample_content
        )
        entry3.tags.add(tag1, tag2)

        # Test filtering by FilterTag1
        url = reverse("journal:entry_list")
        response = self.client.get(url, {"tag": "FilterTag1"})

        self.assertEqual(response.status_code, 200)
        entries = response.context["entries"]
        self.assertEqual(entries.count(), 2)  # entry1 and entry3

        entry_titles = [entry.title for entry in entries]
        self.assertIn("Entry with FilterTag1", entry_titles)
        self.assertIn("Entry with both tags", entry_titles)
        self.assertNotIn("Entry with FilterTag2", entry_titles)

    def test_tag_autocomplete_with_existing_entries(self):
        """Test tag autocomplete functionality with real data"""
        self.client.login(username="testuser", password="testpass123")

        # Create entries with tags
        tags_to_create = ["AutoComplete1", "AutoComplete2", "DifferentTag"]
        for tag_name in tags_to_create:
            tag = Tag.objects.create(user=self.user, name=tag_name)
            entry = JournalEntry.objects.create(
                user=self.user,
                title=f"Entry for {tag_name}",
                content=self.sample_content,
            )
            entry.tags.add(tag)

        # Test autocomplete
        url = reverse("journal:tag_autocomplete")
        response = self.client.get(url, {"q": "AutoComplete"})

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(len(data["tags"]), 2)
        self.assertIn("AutoComplete1", data["tags"])
        self.assertIn("AutoComplete2", data["tags"])
        self.assertNotIn("DifferentTag", data["tags"])


class JournalUserPermissionIntegrationTests(TestCase):
    """Integration tests for user permissions and data isolation"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="user1", email="user1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpass123"
        )

        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {"text": "Test content"},
                }
            ],
            "version": "2.28.2",
        }

        # Create test data for both users
        self.user1_tag = Tag.objects.create(user=self.user1, name="User1Tag")
        self.user2_tag = Tag.objects.create(user=self.user2, name="User2Tag")

        self.user1_entry = JournalEntry.objects.create(
            user=self.user1, title="User1 Entry", content=self.sample_content
        )
        self.user1_entry.tags.add(self.user1_tag)

        self.user2_entry = JournalEntry.objects.create(
            user=self.user2, title="User2 Entry", content=self.sample_content
        )
        self.user2_entry.tags.add(self.user2_tag)

    def test_complete_user_data_isolation(self):
        """Test that users cannot access each other's data through any view"""
        # Login as user1
        self.client.login(username="user1", password="testpass123")

        # Test dashboard isolation
        dashboard_response = self.client.get(reverse("journal:dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertNotContains(dashboard_response, "User2 Entry")

        # Test entry list isolation
        list_response = self.client.get(reverse("journal:entry_list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, "User2 Entry")

        # Test tag autocomplete isolation
        tag_response = self.client.get(
            reverse("journal:tag_autocomplete"), {"q": "User2"}
        )
        data = json.loads(tag_response.content)
        self.assertNotIn("User2Tag", data["tags"])

        # Test direct access to other user's entry (should 404)
        detail_response = self.client.get(
            reverse("journal:entry_detail", kwargs={"entry_id": self.user2_entry.id})
        )
        self.assertEqual(detail_response.status_code, 404)

        # Test direct access to edit other user's entry (should 404)
        edit_response = self.client.get(
            reverse("journal:edit_entry", kwargs={"entry_id": self.user2_entry.id})
        )
        self.assertEqual(edit_response.status_code, 404)

    def test_user_switching_data_isolation(self):
        """Test data isolation when switching between users"""
        # Login as user1, create entry
        self.client.login(username="user1", password="testpass123")

        create_url = reverse("journal:new_entry")
        data = {
            "title": "User1 New Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["User1NewTag"],
        }
        response = self.client.post(create_url, data)
        self.assertEqual(response.status_code, 302)

        # Logout and login as user2
        self.client.logout()
        self.client.login(username="user2", password="testpass123")

        # Verify user2 cannot see user1's new entry
        list_response = self.client.get(reverse("journal:entry_list"))
        self.assertNotContains(list_response, "User1 New Entry")

        # Verify user2 cannot see user1's new tag
        tag_response = self.client.get(
            reverse("journal:tag_autocomplete"), {"q": "User1New"}
        )
        data = json.loads(tag_response.content)
        self.assertNotIn("User1NewTag", data["tags"])

    def test_cross_user_tag_name_collision(self):
        """Test handling of tag name collisions between users"""
        # Both users create tags with the same name
        common_tag_name = "CommonTag"

        # User1 creates tag
        self.client.login(username="user1", password="testpass123")
        create_url = reverse("journal:new_entry")
        data = {
            "title": "User1 Common Tag Entry",
            "content": json.dumps(self.sample_content),
            # Don't include is_public for unchecked checkbox (defaults to False)
            "tags": [common_tag_name],
        }
        response = self.client.post(create_url, data)
        self.assertEqual(response.status_code, 302)

        # User2 creates tag with same name
        self.client.logout()
        self.client.login(username="user2", password="testpass123")
        data2 = {
            "title": "User2 Common Tag Entry",
            "content": json.dumps(self.sample_content),
            "tags": [common_tag_name],
        }
        response = self.client.post(create_url, data2)
        self.assertEqual(response.status_code, 302)

        # Verify both tags exist but are separate
        user1_tag = Tag.objects.get(user=self.user1, name=common_tag_name)
        user2_tag = Tag.objects.get(user=self.user2, name=common_tag_name)

        self.assertNotEqual(user1_tag.id, user2_tag.id)

        # Verify each user only sees their own tag in autocomplete
        tag_response = self.client.get(
            reverse("journal:tag_autocomplete"), {"q": "Common"}
        )
        data = json.loads(tag_response.content)
        self.assertIn(common_tag_name, data["tags"])
        self.assertEqual(len([t for t in data["tags"] if t == common_tag_name]), 1)


class JournalPerformanceIntegrationTests(TransactionTestCase):
    """Integration tests for performance under various conditions"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {"text": "Test content"},
                }
            ],
            "version": "2.28.2",
        }

    def test_dashboard_performance_with_many_entries(self):
        """Test dashboard performance with large number of entries"""
        self.client.login(username="testuser", password="testpass123")

        # Create many entries
        entries = []
        tags = []

        for i in range(100):
            tag = Tag.objects.create(user=self.user, name=f"Tag{i}")
            tags.append(tag)

            entry = JournalEntry.objects.create(
                user=self.user, title=f"Entry {i}", content=self.sample_content
            )
            entry.tags.add(tag)
            entries.append(entry)

        # Measure dashboard load time
        start_time = time.time()
        response = self.client.get(reverse("journal:dashboard"))
        end_time = time.time()

        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 2.0)  # Should load within 2 seconds

        # Verify dashboard shows correct counts
        context = response.context
        self.assertEqual(context["total_entries"], 100)
        self.assertEqual(context["total_tags"], 100)
        self.assertEqual(len(context["recent_entries"]), 5)  # Should limit to 5
        self.assertEqual(len(context["recent_tags"]), 10)  # Should limit to 10

    def test_entry_list_performance_with_filtering(self):
        """Test entry list performance with filtering on large dataset"""
        self.client.login(username="testuser", password="testpass123")

        # Create entries with various tags
        common_tag = Tag.objects.create(user=self.user, name="CommonTag")
        rare_tag = Tag.objects.create(user=self.user, name="RareTag")

        for i in range(200):
            entry = JournalEntry.objects.create(
                user=self.user, title=f"Test Entry {i}", content=self.sample_content
            )

            # Add common tag to most entries
            if i % 3 != 0:
                entry.tags.add(common_tag)

            # Add rare tag to few entries
            if i % 20 == 0:
                entry.tags.add(rare_tag)

        # Test filtering performance
        start_time = time.time()
        response = self.client.get(reverse("journal:entry_list"), {"tag": "RareTag"})
        end_time = time.time()

        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 1.0)  # Should filter within 1 second

        # Verify correct filtering
        entries = response.context["entries"]
        self.assertEqual(entries.count(), 10)  # 200/20 = 10 entries with RareTag

    def test_tag_autocomplete_performance_scaling(self):
        """Test tag autocomplete performance with many tags"""
        self.client.login(username="testuser", password="testpass123")

        # Create many tags with common prefixes
        for i in range(1000):
            Tag.objects.create(user=self.user, name=f"AutoTag{i:04d}")

        # Test autocomplete performance
        start_time = time.time()
        response = self.client.get(
            reverse("journal:tag_autocomplete"), {"q": "AutoTag"}
        )
        end_time = time.time()

        self.assertEqual(response.status_code, 200)
        self.assertLess(
            end_time - start_time, 0.5
        )  # Should complete within 0.5 seconds

        # Verify response limits results
        data = json.loads(response.content)
        self.assertEqual(len(data["tags"]), 10)  # Should limit to 10 results


class JournalErrorHandlingIntegrationTests(TestCase):
    """Integration tests for error handling and recovery"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {"text": "Test content"},
                }
            ],
            "version": "2.28.2",
        }

    def test_database_error_handling_during_creation(self):
        """Test handling of database errors during entry creation"""
        self.client.login(username="testuser", password="testpass123")

        url = reverse("journal:new_entry")
        data = {
            "title": "Error Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["ErrorTag"],
        }

        # Mock database error
        with patch("journal.models.JournalEntry.objects.create") as mock_create:
            mock_create.side_effect = IntegrityError("Database error")

            response = self.client.post(url, data)

            # Should handle error gracefully
            self.assertEqual(response.status_code, 200)  # Returns to form
            messages = list(get_messages(response.wsgi_request))
            self.assertTrue(any("Error creating" in str(msg) for msg in messages))

            # Verify entry was not created
            self.assertFalse(
                JournalEntry.objects.filter(title="Error Test Entry").exists()
            )

    def test_concurrent_tag_creation_handling(self):
        """Test handling of concurrent tag creation scenarios"""
        self.client.login(username="testuser", password="testpass123")

        url = reverse("journal:new_entry")
        data = {
            "title": "Concurrent Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["ConcurrentTag"],
        }

        # Simulate race condition in tag creation
        with patch("journal.models.Tag.objects.get_or_create") as mock_get_or_create:
            # First call succeeds, second call raises IntegrityError (race condition)
            tag = Tag.objects.create(user=self.user, name="ConcurrentTag")
            mock_get_or_create.side_effect = [
                (tag, False),  # Found existing tag
                IntegrityError("UNIQUE constraint failed"),
            ]

            response = self.client.post(url, data)

            # Should handle race condition gracefully
            self.assertIn(response.status_code, [200, 302])

    def test_invalid_data_recovery(self):
        """Test recovery from invalid data submissions"""
        self.client.login(username="testuser", password="testpass123")

        # Test with various invalid data scenarios
        invalid_data_sets = [
            {
                "title": "",  # Empty title
                "content": json.dumps(self.sample_content),
                "tags": ["Test"],
            },
            {"title": "Valid Title", "content": "", "tags": ["Test"]},  # Empty content
            {
                "title": "Valid Title",
                "content": "invalid json content",  # Invalid JSON
                "tags": ["Test"],
            },
        ]

        url = reverse("journal:new_entry")

        for invalid_data in invalid_data_sets:
            response = self.client.post(url, invalid_data)

            # Should return to form with error message
            self.assertEqual(response.status_code, 200)

            # Form should still be usable after error
            self.assertContains(response, "Create New Entry")  # Check page title
            self.assertContains(response, "title")  # Check form field

    def test_session_timeout_handling(self):
        """Test handling of session timeouts during operations"""
        # Login user
        self.client.login(username="testuser", password="testpass123")

        # Simulate session timeout by logging out
        self.client.logout()

        # Try to access protected view
        url = reverse("journal:new_entry")
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

        # Try to submit data without authentication
        data = {
            "title": "Timeout Test Entry",
            "content": json.dumps(self.sample_content),
            "tags": ["TimeoutTag"],
        }

        post_response = self.client.post(url, data)

        # Should redirect to login
        self.assertEqual(post_response.status_code, 302)
        self.assertIn("/login/", post_response.url)

        # Verify no entry was created
        self.assertFalse(
            JournalEntry.objects.filter(title="Timeout Test Entry").exists()
        )


class JournalComplexWorkflowIntegrationTests(TestCase):
    """Integration tests for complex workflows involving multiple components"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {"text": "Test content"},
                }
            ],
            "version": "2.28.2",
        }

    def test_complete_journal_management_workflow(self):
        """Test a complete workflow of journal management operations"""
        self.client.login(username="testuser", password="testpass123")

        # Step 1: Create multiple entries with various tags
        entries_data = [
            {
                "title": "Work Meeting Notes",
                "tags": ["Work", "Meetings", "Important"],
                "is_public": False,
            },
            {
                "title": "Personal Reflection",
                "tags": ["Personal", "Reflection"],
                "is_public": False,
            },
            {
                "title": "Project Ideas",
                "tags": ["Work", "Ideas", "Projects"],
                "is_public": True,
            },
            {
                "title": "Daily Journal",
                "tags": ["Personal", "Daily"],
                "is_public": False,
            },
        ]

        created_entries = []
        for entry_data in entries_data:
            url = reverse("journal:new_entry")
            post_data = {
                "title": entry_data["title"],
                "content": json.dumps(self.sample_content),
                "tags": entry_data["tags"],
                "is_public": "on" if entry_data["is_public"] else "",
            }

            response = self.client.post(url, post_data)
            self.assertEqual(response.status_code, 302)

            entry = JournalEntry.objects.get(title=entry_data["title"])
            created_entries.append(entry)

            # Verify tags were created and assigned
            self.assertEqual(entry.tags.count(), len(entry_data["tags"]))
            self.assertEqual(entry.is_public, entry_data["is_public"])

        # Step 2: Verify dashboard shows correct summary
        dashboard_response = self.client.get(reverse("journal:dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)

        context = dashboard_response.context
        self.assertEqual(context["total_entries"], 4)
        self.assertGreaterEqual(context["total_tags"], 6)  # At least 6 unique tags

        # Step 3: Test filtering functionality
        list_url = reverse("journal:entry_list")

        # Filter by 'Work' tag
        work_response = self.client.get(list_url, {"tag": "Work"})
        work_entries = work_response.context["entries"]
        self.assertEqual(
            work_entries.count(), 2
        )  # Work Meeting Notes and Project Ideas

        # Filter by 'Personal' tag
        personal_response = self.client.get(list_url, {"tag": "Personal"})
        personal_entries = personal_response.context["entries"]
        self.assertEqual(
            personal_entries.count(), 2
        )  # Personal Reflection and Daily Journal

        # Search functionality
        search_response = self.client.get(list_url, {"search": "Meeting"})
        search_entries = search_response.context["entries"]
        self.assertEqual(search_entries.count(), 1)  # Work Meeting Notes

        # Step 4: Test tag autocomplete with real data
        tag_response = self.client.get(
            reverse("journal:tag_autocomplete"), {"q": "Work"}
        )
        data = json.loads(tag_response.content)
        self.assertIn("Work", data["tags"])

        # Step 5: Edit an entry to change tags and privacy
        entry_to_edit = created_entries[0]  # Work Meeting Notes
        edit_url = reverse("journal:edit_entry", kwargs={"entry_id": entry_to_edit.id})

        edit_data = {
            "title": "Updated Work Meeting Notes",
            "content": json.dumps(self.sample_content),
            "tags": ["Work", "Updated", "Completed"],  # Changed tags
            "is_public": "on",  # Made public
        }

        edit_response = self.client.post(edit_url, edit_data)
        self.assertEqual(edit_response.status_code, 302)

        # Verify changes
        entry_to_edit.refresh_from_db()
        self.assertEqual(entry_to_edit.title, "Updated Work Meeting Notes")
        self.assertTrue(entry_to_edit.is_public)
        self.assertEqual(entry_to_edit.tags.count(), 3)

        tag_names = [tag.name for tag in entry_to_edit.tags.all()]
        self.assertIn("Updated", tag_names)
        self.assertIn("Completed", tag_names)
        self.assertNotIn("Meetings", tag_names)  # Should be removed

        # Step 6: Verify filtering reflects changes
        updated_response = self.client.get(list_url, {"tag": "Updated"})
        updated_entries = updated_response.context["entries"]
        self.assertEqual(updated_entries.count(), 1)
        self.assertEqual(updated_entries.first().title, "Updated Work Meeting Notes")

    def test_bulk_operations_workflow(self):
        """Test workflow involving bulk operations and data consistency"""
        self.client.login(username="testuser", password="testpass123")

        # Create base data
        base_tags = ["Category1", "Category2", "Category3"]
        for tag_name in base_tags:
            Tag.objects.create(user=self.user, name=tag_name)

        # Create multiple entries quickly
        entries_count = 20
        for i in range(entries_count):
            url = reverse("journal:new_entry")
            data = {
                "title": f"Bulk Entry {i:02d}",
                "content": json.dumps(self.sample_content),
                "tags": [f"Category{(i % 3) + 1}", f"Sequence{i}"],
                "is_public": "on" if i % 2 == 0 else "",
            }

            response = self.client.post(url, data)
            self.assertEqual(response.status_code, 302)

        # Verify all entries were created
        total_entries = JournalEntry.objects.filter(user=self.user).count()
        self.assertEqual(total_entries, entries_count)

        # Verify tag relationships are correct
        for i in range(entries_count):
            entry = JournalEntry.objects.get(title=f"Bulk Entry {i:02d}")
            self.assertEqual(entry.tags.count(), 2)

            tag_names = [tag.name for tag in entry.tags.all()]
            self.assertIn(f"Category{(i % 3) + 1}", tag_names)
            self.assertIn(f"Sequence{i}", tag_names)

        # Test that filtering still works correctly with bulk data
        category1_response = self.client.get(
            reverse("journal:entry_list"), {"tag": "Category1"}
        )
        category1_count = category1_response.context["entries"].count()
        expected_category1_count = len([i for i in range(entries_count) if i % 3 == 0])
        self.assertEqual(category1_count, expected_category1_count)

        # Test dashboard performance with bulk data
        dashboard_response = self.client.get(reverse("journal:dashboard"))
        self.assertEqual(dashboard_response.status_code, 200)

        context = dashboard_response.context
        self.assertEqual(context["total_entries"], entries_count)
        self.assertEqual(len(context["recent_entries"]), min(5, entries_count))
        self.assertEqual(
            len(context["recent_tags"]), min(10, 3 + entries_count)
        )  # 3 base + sequence tags
