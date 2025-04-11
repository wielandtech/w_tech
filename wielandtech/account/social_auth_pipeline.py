from social_core.pipeline.user import create_user
from social_core.pipeline.social_auth import create_social_auth
from .models import Profile

def create_profile(strategy, details, user=None, *args, **kwargs):
    if user and not hasattr(user, 'profile'):
        Profile.objects.create(user=user)
    return {'user': user} 