"""
Custom middleware for security and access control.
"""
from django.http import HttpResponseForbidden
from django.conf import settings


class RestrictAdminMiddleware:
    """
    Restrict Django admin access to internal domains only.
    Public access to /admin/ is blocked.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # Define allowed hosts for admin access
        self.allowed_admin_hosts = [
            'wielandtech.k8s.local',
            '127.0.0.1',
            'localhost',
        ]

    def __call__(self, request):
        # Check if accessing admin URLs
        if request.path.startswith('/admin/'):
            host = request.get_host().split(':')[0]  # Remove port if present
            
            # Block access if not from allowed internal domain
            if host not in self.allowed_admin_hosts and not settings.DEBUG:
                return HttpResponseForbidden(
                    '<h1>403 Forbidden</h1>'
                    '<p>Admin access is restricted to internal network only.</p>'
                )
        
        response = self.get_response(request)
        return response


class SecurityHeadersMiddleware:
    """
    Add additional security headers for public-facing traffic.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add CSP for public domains only
        host = request.get_host().split(':')[0]
        if host in ['wielandtech.com', 'www.wielandtech.com']:
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self';"
            )
        
        return response

