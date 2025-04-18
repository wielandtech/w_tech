from .models import Profile


def create_profile(strategy, details, user=None, *args, **kwargs):
    if user and not hasattr(user, 'profile'):
        Profile.objects.create(user=user)
    return {'user': user}
