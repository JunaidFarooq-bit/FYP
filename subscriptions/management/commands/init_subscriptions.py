"""
Management command to initialize subscription system.
Run this after adding the subscriptions app.
"""
from django.core.management.base import BaseCommand
from subscriptions.services.subscription_service import SubscriptionService


class Command(BaseCommand):
    help = 'Initialize subscription tiers and create subscriptions for existing users'

    def handle(self, *args, **options):
        self.stdout.write('Creating default subscription tiers...')
        created = SubscriptionService.create_default_tiers()
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created tiers: {", ".join(created)}')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('All tiers already exist.')
            )
        
        self.stdout.write('\nDone! You can now use the subscription system.')
