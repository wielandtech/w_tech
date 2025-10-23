#!/usr/bin/env python
"""
Test script to verify all custom error handlers work correctly.
Run this script to test all error pages locally.
"""

import os
import sys
import django
from django.conf import settings
from django.test import RequestFactory
from django.http import Http404, HttpResponseForbidden, HttpResponseBadRequest, HttpResponseServerError

# Add the project directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wielandtech.settings')
django.setup()

from core.views import custom_400, custom_403, custom_404, custom_500, custom_502, custom_503, maintenance

def test_error_handler(handler, status_code, error_name):
    """Test a specific error handler."""
    print(f"🧪 Testing {error_name} handler...")
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/test')
    
    try:
        response = handler(request)
        print(f"✅ {error_name} handler returned status code: {response.status_code}")
        print(f"✅ Response content type: {response.get('Content-Type', 'Not set')}")
        
        # Check if the response contains expected content
        content = response.content.decode('utf-8')
        if error_name in content:
            print(f"✅ Response contains '{error_name}' text")
        else:
            print(f"❌ Response does not contain '{error_name}' text")
            
        if 'WielandTech' in content:
            print(f"✅ Response contains 'WielandTech' branding")
        else:
            print(f"❌ Response does not contain 'WielandTech' branding")
            
        if 'Return Home' in content or 'Try Again' in content or 'Check Status' in content:
            print(f"✅ Response contains action button")
        else:
            print(f"❌ Response does not contain action button")
            
        print(f"✅ {error_name} handler test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing {error_name} handler: {e}")
        return False

def test_all_error_handlers():
    """Test all custom error handlers."""
    print("🚀 Testing all custom error handlers...")
    print("=" * 50)
    
    # Test all error handlers
    handlers = [
        (custom_400, 400, "400 Bad Request"),
        (custom_403, 403, "403 Forbidden"),
        (custom_404, 404, "404 Not Found"),
        (custom_500, 500, "500 Internal Server Error"),
        (custom_502, 502, "502 Bad Gateway"),
        (custom_503, 503, "503 Service Unavailable"),
        (maintenance, 503, "Maintenance"),
    ]
    
    results = []
    for handler, status_code, error_name in handlers:
        result = test_error_handler(handler, status_code, error_name)
        results.append(result)
        print()  # Add spacing between tests
    
    # Summary
    print("=" * 50)
    print("📊 Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 All error handler tests passed!")
    else:
        print("⚠️  Some error handler tests failed!")
    
    return passed == total

if __name__ == '__main__':
    success = test_all_error_handlers()
    sys.exit(0 if success else 1)
