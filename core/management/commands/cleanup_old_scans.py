"""
Django management command to clean up old scan records
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import MediaScan


class Command(BaseCommand):
    help = 'Delete scan records older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete scans older than this many days (default: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        cutoff_date = timezone.now() - timedelta(days=days)
        old_scans = MediaScan.objects.filter(created_at__lt=cutoff_date)

        if dry_run:
            self.stdout.write(f'[DRY RUN] Would delete {old_scans.count()} scans older than {days} days')
            for scan in old_scans[:10]:  # Show first 10
                self.stdout.write(f'  - Scan #{scan.id} from {scan.created_at}')
            if old_scans.count() > 10:
                self.stdout.write(f'  ... and {old_scans.count() - 10} more')
        else:
            count = old_scans.count()
            old_scans.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {count} scans older than {days} days'))
