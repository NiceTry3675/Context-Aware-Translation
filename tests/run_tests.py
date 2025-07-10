#!/usr/bin/env python3
"""
Test runner for Context-Aware Translation tests.

Usage:
    python tests/run_tests.py              # Run unit tests only
    python tests/run_tests.py --unit       # Run unit tests only
    python tests/run_tests.py --integration # Run integration tests (requires API key)
    python tests/run_tests.py --all        # Run all tests
"""

import os
import sys
import unittest
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_unit_tests():
    """Run unit tests with mocked API calls."""
    print("\n" + "="*60)
    print("Running Unit Tests (Mocked API)")
    print("="*60 + "\n")
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName('tests.test_translation_overall')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests():
    """Run integration tests with actual API."""
    print("\n" + "="*60)
    print("Running Integration Tests (Real API)")
    print("="*60 + "\n")
    
    # Check for API key
    if not os.environ.get('GEMINI_API_KEY'):
        print("ERROR: GEMINI_API_KEY environment variable not set!")
        print("To run integration tests:")
        print("  export GEMINI_API_KEY='your-api-key'")
        print("  python tests/run_tests.py --integration")
        return False
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName('tests.test_integration')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    parser = argparse.ArgumentParser(description='Run Context-Aware Translation tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    
    args = parser.parse_args()
    
    # Default to unit tests if no option specified
    if not any([args.unit, args.integration, args.all]):
        args.unit = True
    
    success = True
    
    if args.unit or args.all:
        unit_success = run_unit_tests()
        success = success and unit_success
    
    if args.integration or args.all:
        integration_success = run_integration_tests()
        success = success and integration_success
    
    # Summary
    print("\n" + "="*60)
    if success:
        print("All tests passed! ✓")
    else:
        print("Some tests failed! ✗")
    print("="*60 + "\n")
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()