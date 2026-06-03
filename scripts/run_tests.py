#!/usr/bin/env python
"""
Test runner script for WebLift.

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py --unit            # Run only unit tests
    python run_tests.py --integration     # Run only integration tests
    python run_tests.py --seo             # Run SEOAnalyzer tests
    python run_tests.py --keyword         # Run keyword_ai tests
    python run_tests.py --comparative     # Run comparative_analysis tests
    python run_tests.py --subscription    # Run subscriptions tests
    python run_tests.py --coverage        # Run with coverage report
    python run_tests.py --verbose         # Verbose output
"""

import sys
import subprocess
import argparse


def run_command(cmd, description):
    """Run a shell command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode != 0:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return False
    
    print(f"\n✅ {description} completed successfully")
    return True


def main():
    parser = argparse.ArgumentParser(description='WebLift Test Runner')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--e2e', action='store_true', help='Run E2E tests only')
    parser.add_argument('--seo', action='store_true', help='Run SEOAnalyzer tests')
    parser.add_argument('--keyword', action='store_true', help='Run keyword_ai tests')
    parser.add_argument('--comparative', action='store_true', help='Run comparative_analysis tests')
    parser.add_argument('--subscription', action='store_true', help='Run subscriptions tests')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--failfast', '-x', action='store_true', help='Stop on first failure')
    parser.add_argument('--parallel', '-n', type=int, default=None, help='Number of parallel processes')
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ['pytest']
    
    # Add verbose flag
    if args.verbose:
        base_cmd.append('-v')
    
    # Add failfast flag
    if args.failfast:
        base_cmd.append('-x')
    
    # Add parallel execution
    if args.parallel:
        base_cmd.extend(['-n', str(args.parallel)])
    
    # Determine which tests to run
    test_paths = []
    markers = []
    
    if args.seo:
        test_paths.append('SEOAnalyzer/tests')
    elif args.keyword:
        test_paths.append('keyword_ai/tests')
    elif args.comparative:
        test_paths.append('comparative_analysis/tests')
    elif args.subscription:
        test_paths.append('subscriptions/tests')
    else:
        # Run all tests
        test_paths = [
            'SEOAnalyzer/tests',
            'keyword_ai/tests',
            'comparative_analysis/tests',
            'subscriptions/tests'
        ]
    
    # Add markers
    if args.unit:
        markers.append('unit')
    elif args.integration:
        markers.append('integration')
    elif args.e2e:
        markers.append('e2e')
    
    # Build command
    cmd = base_cmd.copy()
    
    if markers:
        cmd.extend(['-m', ' or '.join(markers)])
    
    cmd.extend(test_paths)
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend([
            '--cov=.',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov',
            '--cov-report=xml:coverage.xml',
        ])
    
    # Join command
    full_cmd = ' '.join(cmd)
    
    print("\n" + "="*60)
    print("WebLift Test Runner")
    print("="*60)
    print(f"Command: {full_cmd}")
    
    # Run tests
    success = run_command(full_cmd, "Test Suite")
    
    if args.coverage and success:
        print("\n📊 Coverage reports generated:")
        print("   - Terminal: See above")
        print("   - HTML: htmlcov/index.html")
        print("   - XML: coverage.xml")
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
