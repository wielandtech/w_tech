from .settings import *

DEBUG = True

# Disable HTTPS-related settings
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
SECURE_PROXY_SSL_HEADER = None
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Update CSRF trusted origins to include HTTP
CSRF_TRUSTED_ORIGINS = [
    "http://dev.wielandtech.com:8080",
    "http://dev.wielandtech.com:8443",
    "http://localhost:8080",
]

# Update Social Auth settings
SOCIAL_AUTH_REDIRECT_IS_HTTPS = False
