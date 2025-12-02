#!/usr/bin/env python
"""
Quick test script to verify the create_test_data management command works.
This will be deleted after testing.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'onespirit_project.settings.dev')
django.setup()

def test_management_command():
    """Test the create_test_data management command"""
    print("Testing create_test_data management command...")
    
    try:
        # Test basic scenario with minimal data
        print("\n1. Testing basic scenario creation...")
        execute_from_command_line([
            'manage.py', 'create_test_data', 
            '--scenario', 'basic',
            '--tenants', '1',
            '--members', '3',
            '--clubs', '1',
            '--no-payments'  # Skip payments for quick test
        ])
        print("✓ Basic test data creation successful!")
        
        # Test clearing data
        print("\n2. Testing data clearing...")
        execute_from_command_line([
            'manage.py', 'create_test_data', 
            '--clear-existing',
            '--scenario', 'minimal',
            '--tenants', '1',
            '--members', '2',
            '--clubs', '1'
        ])
        print("✓ Data clearing and recreation successful!")
        
        print("\n🎉 All tests passed! Management command is working correctly.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_management_command()
    if success:
        print("\nYou can now use the management command:")
        print("python manage.py create_test_data --help")
        print("python manage.py create_test_data --scenario basic")
    sys.exit(0 if success else 1)