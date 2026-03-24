#!/usr/bin/env python3
"""Test runner for nitter-twitter-search.

This script runs all unit tests and provides a summary.

Usage:
    python test_runner.py              # Run all tests
    python test_runner.py -v           # Verbose output
    python test_runner.py -k test_name # Filter by name
    python test_runner.py tests/test_url_building.py  # Run specific file
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_tests():
    """Run all tests with pytest."""
    import pytest
    
    # Get test directory
    test_dir = os.path.dirname(__file__)
    
    # Run pytest with verbose output and coverage
    return pytest.main([
        test_dir,
        '-v',                           # Verbose
        '--tb=short',                   # Short tracebacks
        '--showlocals',                 # Show local variables
        '-ra',                          # Show all failures
        '--strict-markers',             # Strict markers
        '--color=yes',                  # Colored output
    ])


def main():
    """Main entry point."""
    print("=" * 70)
    print("Running nitter-twitter-search Unit Tests")
    print("=" * 70)
    print()
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("❌ pytest not installed. Installing...")
        os.system('pip install pytest')
        import pytest
    
    # Run tests
    exit_code = run_tests()
    
    print()
    print("=" * 70)
    
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ Tests failed with exit code {exit_code}")
    
    print("=" * 70)
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
