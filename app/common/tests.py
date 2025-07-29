from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db.utils import OperationalError
from unittest.mock import patch
from io import StringIO


class WaitForDbTests(TestCase):
    """Test the wait_for_db management command."""

    def test_wait_for_db_ready(self):
        """Test waiting for database when database is available."""
        with patch('django.core.management.base.BaseCommand.check') as patched_check:
            patched_check.return_value = True
            call_command('wait_for_db')
            patched_check.assert_called_once_with(databases=['default'])

    @patch('time.sleep')
    def test_wait_for_db_delay(self, patched_sleep):
        """Test waiting for database when getting OperationalError."""
        with patch('django.core.management.base.BaseCommand.check') as patched_check:
            patched_check.side_effect = [OperationalError] * 2 + [True]
            call_command('wait_for_db')
            self.assertEqual(patched_check.call_count, 3)
            patched_check.assert_called_with(databases=['default'])

    @patch('time.sleep')
    def test_wait_for_db_timeout(self, patched_sleep):
        """Test that command fails after timeout."""
        with patch('django.core.management.base.BaseCommand.check') as patched_check:
            patched_check.side_effect = OperationalError
            with patch('time.time') as patched_time:
                # Mock time to simulate timeout
                patched_time.side_effect = [0, 31]  # Start time, then after timeout
                
                with self.assertRaises(SystemExit):
                    call_command('wait_for_db', timeout=30)
