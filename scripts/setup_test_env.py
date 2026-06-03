#!/usr/bin/env python
"""
Setup script for WebLift test environment.

This script:
1. Checks Python version
2. Installs test dependencies
3. Creates test directories
4. Runs database migrations for test database
5. Verifies test configuration

Usage:
    python setup_test_env.py
"""

import sys
import os
import subprocess
from pathlib import Path


def check_python_version():
    """Check if Python version is compatible."""
    print("Checking Python version...")
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print(f"❌ Python {version.major}.{version.minor} is not supported.")
        print("   Required: Python 3.10 or higher")
        return False
    
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install test dependencies."""
    print("\nInstalling test dependencies...")
    
    commands = [
        [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
        [sys.executable, '-m', 'pip', 'install', '-r', 'requirements-test.txt'],
    ]
    
    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Failed to install dependencies:")
            print(result.stderr)
            return False
    
    print("✅ Dependencies installed")
    return True


def create_test_directories():
    """Create necessary test directories."""
    print("\nCreating test directories...")
    
    directories = [
        'test_media',
        'test_static',
        'test_data',
    ]
    
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"  ✓ {dir_name}/")
    
    return True


def run_migrations():
    """Run database migrations for test database."""
    print("\nRunning database migrations...")
    
    # Set test settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'Project.settings_test'
    
    try:
        import django
        django.setup()
        
        from django.core.management import call_command
        call_command('migrate', '--run-syncdb', verbosity=0)
        
        print("✅ Migrations completed")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False


def verify_test_configuration():
    """Verify test configuration is working."""
    print("\nVerifying test configuration...")
    
    os.environ['DJANGO_SETTINGS_MODULE'] = 'Project.settings_test'
    
    try:
        import django
        django.setup()
        
        # Try to create a test user
        from django.contrib.auth.models import User
        
        # Check if we can access the database
        user_count = User.objects.count()
        print(f"  ✓ Database connection working ({user_count} users)")
        
        # Check if test settings are loaded
        from django.conf import settings
        
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
            print("  ✓ Test database configured (SQLite)")
        
        if settings.CELERY_TASK_ALWAYS_EAGER:
            print("  ✓ Celery configured for synchronous execution")
        
        print("  ✓ Test configuration verified")
        return True
        
    except Exception as e:
        print(f"❌ Configuration verification failed: {e}")
        return False


def run_smoke_tests():
    """Run a quick smoke test."""
    print("\nRunning smoke tests...")
    
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-x', '-q', '--tb=line'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Smoke tests passed")
        return True
    else:
        print("⚠️  Some smoke tests failed (this is OK if no tests exist yet)")
        print(result.stdout)
        return True  # Don't fail setup if tests don't exist


def print_next_steps():
    """Print next steps for the user."""
    print("\n" + "="*60)
    print("Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Run all tests:")
    print("     python run_tests.py")
    print("\n  2. Run specific module tests:")
    print("     python run_tests.py --seo")
    print("     python run_tests.py --keyword")
    print("     python run_tests.py --comparative")
    print("     python run_tests.py --subscription")
    print("\n  3. Run with coverage:")
    print("     python run_tests.py --coverage")
    print("\n  4. Run unit tests only:")
    print("     python run_tests.py --unit")
    print("\n  5. Run tests in parallel:")
    print("     python run_tests.py --parallel 4")
    print("\n" + "="*60)


def main():
    """Main setup function."""
    print("="*60)
    print("WebLift Test Environment Setup")
    print("="*60)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n⚠️  Continuing without installing dependencies...")
    
    # Create test directories
    create_test_directories()
    
    # Run migrations
    if not run_migrations():
        print("\n❌ Setup failed at migrations")
        sys.exit(1)
    
    # Verify configuration
    if not verify_test_configuration():
        print("\n❌ Setup failed at verification")
        sys.exit(1)
    
    # Run smoke tests
    run_smoke_tests()
    
    # Print next steps
    print_next_steps()
    
    sys.exit(0)


if __name__ == '__main__':
    main()
