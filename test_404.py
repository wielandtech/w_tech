#!/usr/bin/env python
"""
Test script to verify the custom 404 handler works correctly.
Run this script to test the 404 page locally.
"""

import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory
from django.http import Http404

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wielandtech.settings')
django.setup()

from core.views import custom_404

def test_404_handler():
    """Test the custom 404 handler."""
    print("🧪 Testing custom 404 handler...")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/nonexistent-page')
    
    # Test the 404 handler
    try:
        response = custom_404(request)
        print(f"✅ 404 handler returned status code: {response.status_code}")
        print(f"✅ Response content type: {response.get('Content-Type', 'Not set')}")
        
        # Check if the response contains expected content
        content = response.content.decode('utf-8')
        if '404 Not Found' in content:
            print("✅ Response contains '404 Not Found' text")
        else:
            print("❌ Response does not contain '404 Not Found' text")
            
        if 'WielandTech' in content:
            print("✅ Response contains 'WielandTech' branding")
        else:
            print("❌ Response does not contain 'WielandTech' branding")
            
        if 'Return Home' in content:
            print("✅ Response contains 'Return Home' button")
        else:
            print("❌ Response does not contain 'Return Home' button")
            
        print("\n🎉 404 handler test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing 404 handler: {e}")
        return False

if __name__ == '__main__':
    success = test_404_handler()
    sys.exit(0 if success else 1)

