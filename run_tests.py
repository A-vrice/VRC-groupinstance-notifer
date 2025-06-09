#!/usr/bin/env python3
"""
Test runner for VRC Group Instance Notifier

This script runs all unit tests for the project.
"""

import unittest
import sys
import os

def main():
    """Run all tests"""
    # Add current directory to path so we can import modules
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = os.path.dirname(os.path.abspath(__file__))
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == '__main__':
    main()