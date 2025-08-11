import json
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from uuid import UUID

from journal.models import Tag, JournalEntry

User = get_user_model()


class TagModelUnitTests(TestCase):
    """Unit tests for the Tag model"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
    
    def test_tag_creation(self):
        """Test basic tag creation"""
        tag = Tag.objects.create(
            user=self.user1,
            name='Personal'
        )
        
        self.assertEqual(tag.name, 'Personal')
        self.assertEqual(tag.user, self.user1)
        self.assertIsNotNone(tag.created_at)
        self.assertIsNotNone(tag.updated_at)
    
    def test_tag_str_representation(self):
        """Test string representation of tag"""
        tag = Tag.objects.create(
            user=self.user1,
            name='Work'
        )
        
        self.assertEqual(str(tag), 'Work')
    
    def test_tag_name_max_length(self):
        """Test tag name maximum length constraint"""
        long_name = 'x' * 101  # Exceeds max_length of 100
        
        with self.assertRaises(ValidationError):
            tag = Tag(user=self.user1, name=long_name)
            tag.full_clean()
    
    def test_tag_name_uniqueness(self):
        """Test that tag names must be unique per user"""
        Tag.objects.create(user=self.user1, name='Unique')
        
        # Same user cannot create duplicate tag
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tag.objects.create(user=self.user1, name='Unique')
        
        # But different users can create tags with the same name
        tag2 = Tag.objects.create(user=self.user2, name='Unique')
        self.assertEqual(tag2.name, 'Unique')
        self.assertEqual(tag2.user, self.user2)
    
    def test_tag_user_required(self):
        """Test that user field is required"""
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tag.objects.create(name='No User')
    
    def test_tag_ordering(self):
        """Test that tags are ordered by created_at descending"""
        tag1 = Tag.objects.create(user=self.user1, name='First')
        tag2 = Tag.objects.create(user=self.user1, name='Second')
        tag3 = Tag.objects.create(user=self.user1, name='Third')
        
        tags = list(Tag.objects.all())
        self.assertEqual(tags[0], tag3)  # Most recent first
        self.assertEqual(tags[1], tag2)
        self.assertEqual(tags[2], tag1)
    
    def test_tag_cascade_delete(self):
        """Test that tags are deleted when user is deleted"""
        tag = Tag.objects.create(user=self.user1, name='Test Tag')
        tag_id = tag.id
        
        self.user1.delete()
        
        with self.assertRaises(Tag.DoesNotExist):
            Tag.objects.get(id=tag_id)
    
    def test_tag_timestamps_auto_update(self):
        """Test that created_at and updated_at are automatically set"""
        tag = Tag.objects.create(user=self.user1, name='Test')
        original_created = tag.created_at
        original_updated = tag.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        tag.name = 'Updated Test'
        tag.save()
        
        tag.refresh_from_db()
        self.assertEqual(tag.created_at, original_created)  # Should not change
        self.assertGreater(tag.updated_at, original_updated)  # Should be updated


class JournalEntryModelUnitTests(TestCase):
    """Unit tests for the JournalEntry model"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123'
        )
        self.tag1 = Tag.objects.create(user=self.user1, name='Personal')
        self.tag2 = Tag.objects.create(user=self.user1, name='Work')
        
        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "header-1",
                    "type": "header",
                    "data": {
                        "text": "My Journal Entry",
                        "level": 2
                    }
                },
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {
                        "text": "This is my first journal entry content."
                    }
                }
            ],
            "version": "2.28.2"
        }
    
    def test_journal_entry_creation(self):
        """Test basic journal entry creation"""
        entry = JournalEntry.objects.create(
            user=self.user1,
            title='My First Entry',
            content=self.sample_content,
            is_public=False
        )
        
        self.assertEqual(entry.title, 'My First Entry')
        self.assertEqual(entry.user, self.user1)
        self.assertEqual(entry.content, self.sample_content)
        self.assertFalse(entry.is_public)
        self.assertIsNotNone(entry.created_at)
        self.assertIsNotNone(entry.updated_at)
    
    def test_journal_entry_str_representation(self):
        """Test string representation of journal entry"""
        entry = JournalEntry.objects.create(
            user=self.user1,
            title='Test Entry',
            content=self.sample_content
        )
        
        expected_str = f"Test Entry by {self.user1.username}"
        self.assertEqual(str(entry), expected_str)
    
    def test_journal_entry_title_max_length(self):
        """Test journal entry title maximum length constraint"""
        long_title = 'x' * 256  # Exceeds max_length of 255
        
        with self.assertRaises(ValidationError):
            entry = JournalEntry(
                user=self.user1,
                title=long_title,
                content=self.sample_content
            )
            entry.full_clean()
    
    def test_journal_entry_default_is_public(self):
        """Test that is_public defaults to False"""
        entry = JournalEntry.objects.create(
            user=self.user1,
            title='Test Entry',
            content=self.sample_content
        )
        
        self.assertFalse(entry.is_public)
    
    
    def test_journal_entry_null_fields(self):
        """Test behavior with null/empty values"""
        # Test that empty title string is allowed at database level
        # but not at validation level
        entry = JournalEntry.objects.create(
            user=self.user1,
            title='',  # Empty string
            content=self.sample_content
        )
        self.assertEqual(entry.title, '')
        
        # But full_clean should catch this
        with self.assertRaises(ValidationError):
            entry.full_clean()
    
    def test_journal_entry_json_content(self):
        """Test that content field properly stores JSON data"""
        entry = JournalEntry.objects.create(
            user=self.user1,
            title='JSON Test',
            content=self.sample_content
        )
        
        entry.refresh_from_db()
        self.assertIsInstance(entry.content, dict)
        self.assertEqual(entry.content['version'], '2.28.2')
        self.assertEqual(len(entry.content['blocks']), 2)
    
    def test_journal_entry_ordering(self):
        """Test that entries are ordered by created_at descending"""
        entry1 = JournalEntry.objects.create(
            user=self.user1, title='First', content=self.sample_content
        )
        entry2 = JournalEntry.objects.create(
            user=self.user1, title='Second', content=self.sample_content
        )
        entry3 = JournalEntry.objects.create(
            user=self.user1, title='Third', content=self.sample_content
        )
        
        entries = list(JournalEntry.objects.all())
        self.assertEqual(entries[0], entry3)  # Most recent first
        self.assertEqual(entries[1], entry2)
        self.assertEqual(entries[2], entry1)
    
    def test_journal_entry_cascade_delete(self):
        """Test that entries are deleted when user is deleted"""
        entry = JournalEntry.objects.create(
            user=self.user1,
            title='Test Entry',
            content=self.sample_content
        )
        entry_id = entry.id
        
        self.user1.delete()
        
        with self.assertRaises(JournalEntry.DoesNotExist):
            JournalEntry.objects.get(id=entry_id)
    
    def test_journal_entry_timestamps_auto_update(self):
        """Test that created_at and updated_at are automatically set"""
        entry = JournalEntry.objects.create(
            user=self.user1,
            title='Test',
            content=self.sample_content
        )
        original_created = entry.created_at
        original_updated = entry.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        entry.title = 'Updated Test'
        entry.save()
        
        entry.refresh_from_db()
        self.assertEqual(entry.created_at, original_created)  # Should not change
        self.assertGreater(entry.updated_at, original_updated)  # Should be updated


class TagJournalEntryIntegrationTests(TestCase):
    """Integration tests for Tag and JournalEntry relationship"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.tag1 = Tag.objects.create(user=self.user, name='Personal')
        self.tag2 = Tag.objects.create(user=self.user, name='Work')
        self.tag3 = Tag.objects.create(user=self.user, name='Ideas')
        
        self.sample_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {
                        "text": "This is a test journal entry."
                    }
                }
            ],
            "version": "2.28.2"
        }
    
    def test_journal_entry_tag_assignment(self):
        """Test assigning tags to journal entries"""
        entry = JournalEntry.objects.create(
            user=self.user,
            title='Test Entry',
            content=self.sample_content
        )
        
        # Add tags
        entry.tags.add(self.tag1, self.tag2)
        
        self.assertEqual(entry.tags.count(), 2)
        self.assertIn(self.tag1, entry.tags.all())
        self.assertIn(self.tag2, entry.tags.all())
    
    def test_journal_entry_tag_removal(self):
        """Test removing tags from journal entries"""
        entry = JournalEntry.objects.create(
            user=self.user,
            title='Test Entry',
            content=self.sample_content
        )
        entry.tags.add(self.tag1, self.tag2, self.tag3)
        
        # Remove one tag
        entry.tags.remove(self.tag2)
        
        self.assertEqual(entry.tags.count(), 2)
        self.assertNotIn(self.tag2, entry.tags.all())
        self.assertIn(self.tag1, entry.tags.all())
        self.assertIn(self.tag3, entry.tags.all())
    
    def test_tag_deletion_doesnt_affect_entries(self):
        """Test that deleting a tag doesn't delete associated journal entries"""
        entry = JournalEntry.objects.create(
            user=self.user,
            title='Test Entry',
            content=self.sample_content
        )
        entry.tags.add(self.tag1, self.tag2)
        
        tag1_id = self.tag1.id
        self.tag1.delete()
        
        entry.refresh_from_db()
        self.assertTrue(JournalEntry.objects.filter(id=entry.id).exists())
        self.assertEqual(entry.tags.count(), 1)
        self.assertNotIn(tag1_id, [tag.id for tag in entry.tags.all()])
    
    def test_multiple_entries_same_tags(self):
        """Test that multiple entries can share the same tags"""
        entry1 = JournalEntry.objects.create(
            user=self.user,
            title='Entry 1',
            content=self.sample_content
        )
        entry2 = JournalEntry.objects.create(
            user=self.user,
            title='Entry 2',
            content=self.sample_content
        )
        
        # Both entries use the same tags
        entry1.tags.add(self.tag1, self.tag2)
        entry2.tags.add(self.tag1, self.tag2)
        
        # Verify both entries have the tags
        self.assertEqual(entry1.tags.count(), 2)
        self.assertEqual(entry2.tags.count(), 2)
        
        # Verify tags are associated with both entries
        tag1_entries = self.tag1.journalentry_set.all()
        self.assertIn(entry1, tag1_entries)
        self.assertIn(entry2, tag1_entries)
    
    def test_entry_without_tags(self):
        """Test that journal entries can exist without tags"""
        entry = JournalEntry.objects.create(
            user=self.user,
            title='No Tags Entry',
            content=self.sample_content
        )
        
        self.assertEqual(entry.tags.count(), 0)
        self.assertFalse(entry.tags.exists())
    
    def test_tag_filtering_by_entries(self):
        """Test filtering tags by associated journal entries"""
        entry1 = JournalEntry.objects.create(
            user=self.user,
            title='Entry 1',
            content=self.sample_content
        )
        entry2 = JournalEntry.objects.create(
            user=self.user,
            title='Entry 2',
            content=self.sample_content
        )
        
        entry1.tags.add(self.tag1, self.tag2)
        entry2.tags.add(self.tag2, self.tag3)
        
        # Get tags used by entry1
        entry1_tags = Tag.objects.filter(journalentry=entry1)
        self.assertEqual(entry1_tags.count(), 2)
        self.assertIn(self.tag1, entry1_tags)
        self.assertIn(self.tag2, entry1_tags)
        
        # Get tags used by both entries
        common_tags = Tag.objects.filter(
            journalentry__in=[entry1, entry2]
        ).distinct()
        self.assertEqual(common_tags.count(), 3)  # All tags are used
    
    def test_bulk_tag_operations(self):
        """Test bulk operations with tags and entries"""
        entries = []
        for i in range(5):
            entry = JournalEntry.objects.create(
                user=self.user,
                title=f'Entry {i}',
                content=self.sample_content
            )
            entries.append(entry)
        
        # Bulk assign tags to all entries
        for entry in entries:
            entry.tags.set([self.tag1, self.tag2])
        
        # Verify all entries have the tags
        for entry in entries:
            self.assertEqual(entry.tags.count(), 2)
        
        # Verify tags are associated with all entries
        tag1_entries = self.tag1.journalentry_set.count()
        self.assertEqual(tag1_entries, 5)


class ModelValidationIntegrationTests(TestCase):
    """Integration tests for model validation and constraints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_complex_json_content_validation(self):
        """Test that complex JSON content is properly handled"""
        complex_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "header-1",
                    "type": "header",
                    "data": {
                        "text": "Complex Entry",
                        "level": 1
                    }
                },
                {
                    "id": "list-1",
                    "type": "list",
                    "data": {
                        "style": "unordered",
                        "items": ["Item 1", "Item 2", "Item 3"]
                    }
                },
                {
                    "id": "table-1",
                    "type": "table",
                    "data": {
                        "content": [
                            ["Header 1", "Header 2"],
                            ["Cell 1", "Cell 2"]
                        ]
                    }
                }
            ],
            "version": "2.28.2"
        }
        
        entry = JournalEntry.objects.create(
            user=self.user,
            title='Complex Entry',
            content=complex_content
        )
        
        entry.refresh_from_db()
        self.assertEqual(entry.content['blocks'][1]['data']['items'], 
                        ["Item 1", "Item 2", "Item 3"])
        self.assertEqual(len(entry.content['blocks']), 3)
    
    def test_edge_case_empty_content(self):
        """Test handling of empty or minimal content"""
        empty_content = {
            "time": 1643723964077,
            "blocks": [],
            "version": "2.28.2"
        }
        
        entry = JournalEntry.objects.create(
            user=self.user,
            title='Empty Entry',
            content=empty_content
        )
        
        self.assertEqual(len(entry.content['blocks']), 0)
        self.assertEqual(entry.content['version'], '2.28.2')
    
    def test_unicode_content_handling(self):
        """Test that Unicode content is properly handled"""
        unicode_content = {
            "time": 1643723964077,
            "blocks": [
                {
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "data": {
                        "text": "Unicode test: 你好世界 🌍 café naïve résumé"
                    }
                }
            ],
            "version": "2.28.2"
        }
        
        entry = JournalEntry.objects.create(
            user=self.user,
            title='Unicode Test Entry 测试',
            content=unicode_content
        )
        
        entry.refresh_from_db()
        self.assertIn("你好世界", entry.content['blocks'][0]['data']['text'])
        self.assertIn("🌍", entry.content['blocks'][0]['data']['text'])
        self.assertIn("测试", entry.title)
