"""
Management command to reset monthly usage counters.
Run this at the start of each month via cron job.
"""
from django.core.management.base import BaseCommand
from subscriptions.models import UsageTracker


class Command(BaseCommand):
    help = 'Reset monthly usage counters for all users'

    def handle(self, *args, **options):
        trackers = UsageTracker.objects.all()
        reset_count = 0
        
        for tracker in trackers:
            # This will reset if needed based on month change
            tracker.reset_if_needed()
            reset_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Checked and reset usage for {reset_count} users.')
        )
