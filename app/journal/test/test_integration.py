"""
Integration tests for journal application covering models, views, and their interactions.
"""

import json
from django.test import TestCase, TransactionTestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
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
        self.assertEqual(Tag.objects.filter(name="uniquetag").count(), 1)

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
        dashboard_response = self.client.get(reverse("journal:dashboard"), follow=True)
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertNotContains(dashboard_response, "User2 Entry")

        # Test entry list isolation
        list_response = self.client.get(reverse("journal:dashboard"), follow=True)
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
        list_response = self.client.get(reverse("journal:dashboard"), follow=True)
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
        normalized_tag_name = "commontag"  # Tags are normalized to lowercase

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

        # Verify both tags exist but are separate (using normalized name)
        user1_tag = Tag.objects.get(user=self.user1, name=normalized_tag_name)
        user2_tag = Tag.objects.get(user=self.user2, name=normalized_tag_name)

        self.assertNotEqual(user1_tag.id, user2_tag.id)

        # Verify each user only sees their own tag in autocomplete
        tag_response = self.client.get(
            reverse("journal:tag_autocomplete"), {"q": "Common"}
        )
        data = json.loads(tag_response.content)
        self.assertIn(normalized_tag_name, data["tags"])
        self.assertEqual(len([t for t in data["tags"] if t == normalized_tag_name]), 1)


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
        response = self.client.get(reverse("journal:dashboard"), follow=True)
        end_time = time.time()

        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 2.0)  # Should load within 2 seconds

        # Verify dashboard shows correct counts
        context = response.context
        self.assertEqual(context["total_entries"], 100)
        self.assertEqual(context["total_tags"], 100)
        self.assertEqual(len(context["recent_entries"]), 5)  # Should limit to 5
        self.assertEqual(len(context["recent_tags"]), 10)  # Should limit to 10

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
                "tags": ["work", "meetings", "important"],
                "is_public": False,
            },
            {
                "title": "Personal Reflection",
                "tags": ["personal", "reflection"],
                "is_public": False,
            },
            {
                "title": "Project Ideas",
                "tags": ["work", "ideas", "projects"],
                "is_public": True,
            },
            {
                "title": "Daily Journal",
                "tags": ["personal", "daily"],
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
        dashboard_response = self.client.get(reverse("journal:dashboard"), follow=True)
        self.assertEqual(dashboard_response.status_code, 200)

        context = dashboard_response.context
        self.assertEqual(context["total_entries"], 4)
        self.assertGreaterEqual(context["total_tags"], 6)  # At least 6 unique tags

        # Step 3: Test filtering functionality
        list_url = reverse("journal:entry_list")

        # Filter by 'work' tag (tags are normalized to lowercase)
        work_response = self.client.get(list_url, {"tag": "work"})
        work_entries = work_response.context["entries"]
        self.assertEqual(
            work_entries.count(), 2
        )  # Work Meeting Notes and Project Ideas

        # Filter by 'personal' tag (tags are normalized to lowercase)
        personal_response = self.client.get(list_url, {"tag": "personal"})
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
            reverse("journal:tag_autocomplete"), {"q": "work"}
        )
        data = json.loads(tag_response.content)
        self.assertIn("work", data["tags"])

        # Step 5: Edit an entry to change tags and privacy
        entry_to_edit = created_entries[0]  # Work Meeting Notes
        edit_url = reverse("journal:edit_entry", kwargs={"entry_id": entry_to_edit.id})

        edit_data = {
            "title": "Updated Work Meeting Notes",
            "content": json.dumps(self.sample_content),
            "tags": ["work", "updated", "completed"],  # Changed tags (lowercase)
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
        self.assertIn("updated", tag_names)  # Tags are lowercase
        self.assertIn("completed", tag_names)  # Tags are lowercase
        self.assertNotIn("meetings", tag_names)  # Should be removed

        # Step 6: Verify filtering reflects changes
        updated_response = self.client.get(list_url, {"tag": "updated"})
        updated_entries = updated_response.context["entries"]
        self.assertEqual(updated_entries.count(), 1)
        self.assertEqual(updated_entries.first().title, "Updated Work Meeting Notes")
