"""
Django Management Command: Check Moz API Status and Usage
Place this file in: comparative_analysis/management/commands/check_moz_api.py
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache
from datetime import datetime
import requests
import hashlib
import hmac
import base64
import time


class Command(BaseCommand):
    help = 'Check Moz API configuration, credentials, and usage statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test',
            action='store_true',
            help='Make a test API call to verify credentials',
        )
        parser.add_argument(
            '--reset-counter',
            action='store_true',
            help='Reset the monthly API usage counter',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('🔍 MOZ API CONFIGURATION CHECK'))
        self.stdout.write(self.style.SUCCESS('='*70 + '\n'))

        # Check 1: Settings Configuration
        self.check_settings()

        # Check 2: Usage Statistics
        self.check_usage_stats()

        # Check 3: Test API Call (if requested)
        if options['test']:
            self.test_api_call()

        # Reset counter (if requested)
        if options['reset_counter']:
            self.reset_usage_counter()

    def check_settings(self):
        """Check if Moz API settings are configured"""
        self.stdout.write(self.style.HTTP_INFO('\n📋 CONFIGURATION CHECK:'))
        self.stdout.write('-' * 70)

        # Check USE_MOZ_API setting
        use_moz = getattr(settings, 'USE_MOZ_API', False)
        if use_moz:
            self.stdout.write(self.style.SUCCESS('✅ USE_MOZ_API: Enabled'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  USE_MOZ_API: Disabled'))
            self.stdout.write(self.style.WARNING('   → Set USE_MOZ_API = True in settings.py to enable'))

        # Check MOZ_ACCESS_ID
        has_access_id = hasattr(settings, 'MOZ_ACCESS_ID') and settings.MOZ_ACCESS_ID
        if has_access_id:
            access_id = settings.MOZ_ACCESS_ID
            masked_id = f"{access_id[:8]}...{access_id[-4:]}" if len(access_id) > 12 else "***"
            self.stdout.write(self.style.SUCCESS(f'✅ MOZ_ACCESS_ID: {masked_id}'))
        else:
            self.stdout.write(self.style.ERROR('❌ MOZ_ACCESS_ID: Not set'))
            self.stdout.write(self.style.ERROR('   → Add MOZ_ACCESS_ID to your settings.py'))

        # Check MOZ_SECRET_KEY
        has_secret = hasattr(settings, 'MOZ_SECRET_KEY') and settings.MOZ_SECRET_KEY
        if has_secret:
            secret = settings.MOZ_SECRET_KEY
            masked_secret = f"{secret[:4]}...{secret[-4:]}" if len(secret) > 8 else "***"
            self.stdout.write(self.style.SUCCESS(f'✅ MOZ_SECRET_KEY: {masked_secret}'))
        else:
            self.stdout.write(self.style.ERROR('❌ MOZ_SECRET_KEY: Not set'))
            self.stdout.write(self.style.ERROR('   → Add MOZ_SECRET_KEY to your settings.py'))

        # Check monthly limit
        limit = getattr(settings, 'MOZ_API_MONTHLY_LIMIT', 50)
        self.stdout.write(self.style.SUCCESS(f'✅ MOZ_API_MONTHLY_LIMIT: {limit} requests/month'))

        # Overall status
        self.stdout.write('')
        if use_moz and has_access_id and has_secret:
            self.stdout.write(self.style.SUCCESS('🎉 Moz API is FULLY CONFIGURED and READY TO USE!'))
        else:
            self.stdout.write(self.style.ERROR('❌ Moz API is NOT PROPERLY CONFIGURED'))
            self.stdout.write(self.style.WARNING('\n📝 To enable Moz API, add to settings.py:'))
            self.stdout.write(self.style.WARNING('   USE_MOZ_API = True'))
            self.stdout.write(self.style.WARNING('   MOZ_ACCESS_ID = "your_access_id_here"'))
            self.stdout.write(self.style.WARNING('   MOZ_SECRET_KEY = "your_secret_key_here"'))
            self.stdout.write(self.style.WARNING('   MOZ_API_MONTHLY_LIMIT = 50'))

    def check_usage_stats(self):
        """Check current API usage statistics"""
        self.stdout.write(self.style.HTTP_INFO('\n📊 USAGE STATISTICS:'))
        self.stdout.write('-' * 70)

        cache_key = "moz_api_requests_this_month"
        current_count = cache.get(cache_key, 0)
        limit = getattr(settings, 'MOZ_API_MONTHLY_LIMIT', 50)
        remaining = max(0, limit - current_count)
        percentage = (current_count / limit * 100) if limit > 0 else 0

        self.stdout.write(f'📈 Requests used this month: {current_count}/{limit}')
        self.stdout.write(f'📉 Requests remaining: {remaining}')
        self.stdout.write(f'📊 Percentage used: {percentage:.1f}%')

        # Visual progress bar
        bar_length = 50
        filled = int(bar_length * percentage / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        if percentage < 50:
            color = self.style.SUCCESS
        elif percentage < 80:
            color = self.style.WARNING
        else:
            color = self.style.ERROR
        
        self.stdout.write(color(f'[{bar}] {percentage:.1f}%'))

        # Warning if near limit
        if percentage >= 90:
            self.stdout.write(self.style.ERROR('\n⚠️  WARNING: Approaching monthly limit!'))
        elif percentage >= 100:
            self.stdout.write(self.style.ERROR('\n🚫 LIMIT REACHED: API calls will use fallback estimation'))

    def test_api_call(self):
        """Make a test API call to verify credentials"""
        self.stdout.write(self.style.HTTP_INFO('\n🧪 TESTING API CONNECTION:'))
        self.stdout.write('-' * 70)

        if not hasattr(settings, 'MOZ_ACCESS_ID') or not settings.MOZ_ACCESS_ID:
            self.stdout.write(self.style.ERROR('❌ Cannot test: MOZ_ACCESS_ID not configured'))
            return

        if not hasattr(settings, 'MOZ_SECRET_KEY') or not settings.MOZ_SECRET_KEY:
            self.stdout.write(self.style.ERROR('❌ Cannot test: MOZ_SECRET_KEY not configured'))
            return

        test_url = "https://moz.com"
        self.stdout.write(f'📡 Testing with URL: {test_url}')
        self.stdout.write('⏳ Making API request...')

        try:
            # Generate auth header
            access_id = settings.MOZ_ACCESS_ID
            secret_key = settings.MOZ_SECRET_KEY
            expires = int(time.time()) + 300

            string_to_sign = f"{access_id}\n{expires}"
            binary_signature = hmac.new(
                secret_key.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                hashlib.sha1
            ).digest()
            signature = base64.b64encode(binary_signature).decode('utf-8')
            auth_header = f"Basic {base64.b64encode(f'{access_id}:{signature}:{expires}'.encode()).decode()}"

            # Make request
            headers = {
                'Authorization': auth_header,
                'Content-Type': 'application/json'
            }
            payload = {'targets': [test_url]}

            response = requests.post(
                "https://lsapi.seomoz.com/v2/url_metrics",
                json=payload,
                headers=headers,
                timeout=10
            )

            # Check response
            if response.status_code == 200:
                data = response.json()
                if 'results' in data and len(data['results']) > 0:
                    result = data['results'][0]
                    da = result.get('domain_authority', 'N/A')
                    pa = result.get('page_authority', 'N/A')
                    spam = result.get('spam_score', 'N/A')

                    self.stdout.write(self.style.SUCCESS('\n✅ API TEST SUCCESSFUL!'))
                    self.stdout.write(self.style.SUCCESS(f'   Domain Authority: {da}'))
                    self.stdout.write(self.style.SUCCESS(f'   Page Authority: {pa}'))
                    self.stdout.write(self.style.SUCCESS(f'   Spam Score: {spam}'))
                    self.stdout.write(self.style.SUCCESS('\n🎉 Your Moz API credentials are WORKING!'))
                else:
                    self.stdout.write(self.style.WARNING('⚠️  API returned no results'))
            elif response.status_code == 401:
                self.stdout.write(self.style.ERROR('\n❌ AUTHENTICATION FAILED'))
                self.stdout.write(self.style.ERROR('   Your Access ID or Secret Key is incorrect'))
                self.stdout.write(self.style.ERROR('   Please verify your credentials at: https://moz.com/products/api'))
            elif response.status_code == 429:
                self.stdout.write(self.style.ERROR('\n❌ RATE LIMIT EXCEEDED'))
                self.stdout.write(self.style.ERROR('   You have exceeded your API quota'))
            else:
                self.stdout.write(self.style.ERROR(f'\n❌ API ERROR: Status {response.status_code}'))
                self.stdout.write(self.style.ERROR(f'   Response: {response.text}'))

        except requests.exceptions.Timeout:
            self.stdout.write(self.style.ERROR('\n❌ REQUEST TIMEOUT'))
            self.stdout.write(self.style.ERROR('   API request took too long'))
        except requests.exceptions.RequestException as e:
            self.stdout.write(self.style.ERROR(f'\n❌ REQUEST ERROR: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ UNEXPECTED ERROR: {e}'))

    def reset_usage_counter(self):
        """Reset the monthly usage counter"""
        self.stdout.write(self.style.HTTP_INFO('\n🔄 RESETTING USAGE COUNTER:'))
        self.stdout.write('-' * 70)

        cache_key = "moz_api_requests_this_month"
        old_count = cache.get(cache_key, 0)
        
        cache.delete(cache_key)
        
        self.stdout.write(self.style.SUCCESS(f'✅ Counter reset: {old_count} → 0'))
        self.stdout.write(self.style.SUCCESS('   Usage statistics have been cleared'))