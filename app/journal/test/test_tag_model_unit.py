from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError

from journal.models import Tag, JournalEntry

User = get_user_model()


class TagModelUnitTests(TestCase):
    """Unit tests for the Tag model"""

    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username="testuser1", email="test1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="testpass123"
        )

    def test_tag_creation(self):
        """Test basic tag creation"""
        tag = Tag.objects.create(user=self.user1, name="Personal")

        self.assertEqual(tag.name, "personal")  # Name should be normalized to lowercase
        self.assertEqual(tag.user, self.user1)
        self.assertIsNotNone(tag.created_at)
        self.assertIsNotNone(tag.updated_at)

    def test_tag_str_representation(self):
        """Test string representation of tag"""
        tag = Tag.objects.create(user=self.user1, name="work")

        self.assertEqual(str(tag), "work")

    def test_tag_name_max_length(self):
        """Test tag name maximum length constraint"""
        long_name = "x" * 101  # Exceeds max_length of 100

        with self.assertRaises(ValidationError):
            tag = Tag(user=self.user1, name=long_name)
            tag.full_clean()

    def test_tag_name_uniqueness_per_user(self):
        """Test that tag names must be unique per user, but can be shared across users"""
        # Same user cannot have duplicate tag names
        Tag.objects.create(user=self.user1, name="Duplicate")

        # Since save() calls full_clean(), we get ValidationError instead of IntegrityError
        with self.assertRaises(ValidationError):
            Tag.objects.create(user=self.user1, name="Duplicate")

        # Different users can have tags with the same name
        Tag.objects.create(user=self.user2, name="Duplicate")  # This should work

    def test_tag_user_required(self):
        """Test that user field is required"""
        # Since save() calls full_clean(), we get ValidationError instead of IntegrityError
        with self.assertRaises(ValidationError):
            Tag.objects.create(name="No User")

    def test_tag_ordering(self):
        """Test that tags are ordered by created_at descending"""
        tag1 = Tag.objects.create(user=self.user1, name="First")
        tag2 = Tag.objects.create(user=self.user1, name="Second")
        tag3 = Tag.objects.create(user=self.user1, name="Third")

        tags = list(Tag.objects.all())
        self.assertEqual(tags[0], tag3)  # Most recent first
        self.assertEqual(tags[1], tag2)
        self.assertEqual(tags[2], tag1)

    def test_tag_cascade_delete(self):
        """Test that tags are deleted when user is deleted"""
        tag = Tag.objects.create(user=self.user1, name="Test Tag")
        tag_id = tag.id

        self.user1.delete()

        with self.assertRaises(Tag.DoesNotExist):
            Tag.objects.get(id=tag_id)

    def test_tag_timestamps_auto_update(self):
        """Test that created_at and updated_at are automatically set"""
        tag = Tag.objects.create(user=self.user1, name="Test")
        original_created = tag.created_at
        original_updated = tag.updated_at

        # Small delay to ensure timestamp difference
        import time

        time.sleep(0.01)

        tag.name = "Updated Test"
        tag.save()

        tag.refresh_from_db()
        self.assertEqual(tag.created_at, original_created)  # Should not change
        self.assertGreater(tag.updated_at, original_updated)  # Should be updated
