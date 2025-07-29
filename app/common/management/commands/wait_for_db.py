import time
from psycopg2 import OperationalError as Psycopg2OpError
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Django command to wait for database."""

    help = 'Wait for database to be available'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Maximum time to wait for database in seconds (default: 30)'
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=1,
            help='Time to wait between connection attempts in seconds (default: 1)'
        )

    def handle(self, *args, **options):
        """Entry point for command."""
        timeout = options['timeout']
        interval = options['interval']
        
        self.stdout.write('Waiting for database...')
        start_time = time.time()
        db_up = False
        
        while not db_up:
            try:
                # Try to connect to the database
                self.check(databases=['default'])
                db_up = True
            except (Psycopg2OpError, OperationalError):
                elapsed_time = time.time() - start_time
                if elapsed_time >= timeout:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Database unavailable after {timeout} seconds, aborting...'
                        )
                    )
                    raise SystemExit(1)
                
                self.stdout.write(
                    f'Database unavailable, waiting {interval} second(s)... '
                    f'({elapsed_time:.1f}s elapsed)'
                )
                time.sleep(interval)

        self.stdout.write(self.style.SUCCESS('Database available!'))
