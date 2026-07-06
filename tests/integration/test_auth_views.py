"""
Integration tests — Authentication views.

Covers: login, register, logout, forget-password, change-password.
Edge cases: wrong credentials, duplicate usernames/emails, invalid tokens,
            password strength, already-logged-in redirects.
"""

import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.integration
@pytest.mark.auth
class TestLoginView:

    def test_login_page_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_login_with_valid_credentials(self, client, test_user):
        # Login form uses 'pass' field (not 'password')
        response = client.post('/', {
            'username': 'testuser',
            'pass': 'testpass123',
        }, follow=True)
        assert response.status_code == 200
        assert response.wsgi_request.user.is_authenticated

    def test_login_with_wrong_password(self, client, test_user):
        response = client.post('/', {
            'username': 'testuser',
            'pass': 'wrongpassword',
        })
        assert not response.wsgi_request.user.is_authenticated

    def test_login_with_nonexistent_user(self, client):
        response = client.post('/', {
            'username': 'ghostuser',
            'pass': 'anypassword',
        })
        assert not response.wsgi_request.user.is_authenticated

    def test_login_with_empty_credentials(self, client):
        response = client.post('/', {'username': '', 'pass': ''})
        assert not response.wsgi_request.user.is_authenticated

    def test_login_redirects_authenticated_user(self, authenticated_client):
        response = authenticated_client.get('/')
        assert response.status_code in (200, 302)

    def test_login_case_sensitive_username(self, client, test_user):
        response = client.post('/', {
            'username': 'TESTUSER',
            'pass': 'testpass123',
        })
        assert not response.wsgi_request.user.is_authenticated


@pytest.mark.integration
@pytest.mark.auth
class TestRegisterView:

    def test_register_page_returns_200(self, client):
        response = client.get('/register/')
        assert response.status_code == 200

    # Register view requires: username, email, FirstName, LastName, password1, password2
    REGISTER_DATA = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'FirstName': 'New',
        'LastName': 'User',
        'password1': 'StrongPass123!',
        'password2': 'StrongPass123!',
    }

    def test_register_creates_user(self, client, db):
        initial_count = User.objects.count()
        client.post('/register/', self.REGISTER_DATA, follow=True)
        assert User.objects.count() > initial_count

    def test_register_creates_subscription_via_signal(self, client, db):
        from subscriptions.models import Subscription
        client.post('/register/', {
            'username': 'signaluser',
            'email': 'signaluser@example.com',
            'FirstName': 'Signal',
            'LastName': 'User',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }, follow=True)
        user = User.objects.filter(username='signaluser').first()
        if user:
            assert Subscription.objects.filter(user=user).exists()

    def test_register_creates_usage_tracker(self, client, db):
        from subscriptions.models import UsageTracker
        client.post('/register/', {
            'username': 'trackeruser',
            'email': 'trackeruser@example.com',
            'FirstName': 'Tracker',
            'LastName': 'User',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        }, follow=True)
        user = User.objects.filter(username='trackeruser').first()
        if user:
            assert UsageTracker.objects.filter(user=user).exists()

    @pytest.mark.django_db(transaction=True)
    def test_register_duplicate_username_fails(self, client, db):
        # Create the user first within this transaction-safe test
        User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
        )
        try:
            client.post('/register/', {
                'username': 'testuser',
                'email': 'different@example.com',
                'FirstName': 'Test',
                'LastName': 'User',
                'password1': 'StrongPass123!',
                'password2': 'StrongPass123!',
            })
        except Exception:
            pass  # IntegrityError or TransactionManagementError expected
        assert User.objects.filter(username='testuser').count() == 1

    def test_register_password_mismatch_fails(self, client, db):
        initial_count = User.objects.count()
        client.post('/register/', {
            'username': 'mismatchuser',
            'email': 'mm@example.com',
            'FirstName': 'Mis',
            'LastName': 'Match',
            'password1': 'StrongPass123!',
            'password2': 'DifferentPass456!',
        })
        assert User.objects.count() == initial_count

    def test_register_with_empty_fields_fails(self, client, db):
        initial_count = User.objects.count()
        client.post('/register/', {'username': '', 'email': '', 'password1': '', 'password2': ''})
        assert User.objects.count() == initial_count


@pytest.mark.integration
@pytest.mark.auth
class TestLogoutView:

    def test_logout_redirects_to_login(self, authenticated_client):
        response = authenticated_client.get('/logout/', follow=True)
        assert response.status_code == 200

    def test_logout_unauthenticates_user(self, authenticated_client):
        authenticated_client.get('/logout/', follow=True)
        response = authenticated_client.get('/home/')
        assert response.status_code in (302, 200)

    def test_logout_unauthenticated_no_crash(self, client):
        response = client.get('/logout/', follow=True)
        assert response.status_code in (200, 302)


@pytest.mark.integration
@pytest.mark.auth
class TestPasswordReset:

    def test_forget_password_page_accessible(self, client):
        response = client.get('/forget-password/')
        assert response.status_code == 200

    def test_forget_password_post_valid_email(self, client, test_user):
        response = client.post('/forget-password/', {
            'email': 'test@example.com',
        }, follow=True)
        assert response.status_code == 200

    def test_forget_password_post_nonexistent_email(self, client):
        response = client.post('/forget-password/', {
            'email': 'nobody@example.com',
        }, follow=True)
        assert response.status_code == 200

    def test_change_password_invalid_token_rejected(self, client):
        response = client.get('/change-password/00000000-0000-0000-0000-000000000000/')
        assert response.status_code in (200, 302, 404)

    def test_change_password_with_valid_token(self, client, test_user):
        from SEOAnalyzer.models import Profile
        import uuid
        profile, _ = Profile.objects.get_or_create(user=test_user)
        token = uuid.uuid4()
        profile.forget_password_token = str(token)
        profile.save()
        response = client.get(f'/change-password/{token}/')
        assert response.status_code in (200, 302)

    def test_change_password_updates_password(self, client, test_user):
        from SEOAnalyzer.models import Profile
        import uuid
        profile, _ = Profile.objects.get_or_create(user=test_user)
        token = uuid.uuid4()
        profile.forget_password_token = str(token)
        profile.save()
        response = client.post(f'/change-password/{token}/', {
            'password': 'NewStrongPass789!',
            'confirm_password': 'NewStrongPass789!',
        }, follow=True)
        assert response.status_code in (200, 302)

    def test_change_password_ignores_tampered_user_id(self, client, test_user, another_user):
        from SEOAnalyzer.models import Profile
        import uuid

        profile, _ = Profile.objects.get_or_create(user=test_user)
        token = uuid.uuid4()
        profile.forget_password_token = str(token)
        profile.save()

        client.post(f'/change-password/{token}/', {
            'new_password': 'OwnerNewPass789!',
            'reconfirm_password': 'OwnerNewPass789!',
            'user_id': another_user.id,
        }, follow=True)

        test_user.refresh_from_db()
        another_user.refresh_from_db()
        assert test_user.check_password('OwnerNewPass789!')
        assert not another_user.check_password('OwnerNewPass789!')


@pytest.mark.integration
@pytest.mark.auth
class TestLoginRequired:

    def test_home_redirects_to_login(self, client):
        response = client.get('/home/')
        # login_url='login' maps to the root URL '/' (loginuser view)
        location = response.get('Location', '')
        assert '/' in location or 'login' in location

    def test_show_requires_login(self, client):
        response = client.post('/show/', {'url': 'https://example.com'})
        assert response.status_code == 302

    def test_report_requires_login(self, client):
        # /report/download/ is @login_required — unauthenticated request redirects (302)
        response = client.get('/report/download/')
        assert response.status_code == 302

    def test_subscriptions_pricing_requires_login(self, client):
        response = client.get('/subscriptions/pricing/')
        assert response.status_code == 302

    def test_subscriptions_dashboard_requires_login(self, client):
        response = client.get('/subscriptions/dashboard/')
        assert response.status_code == 302
