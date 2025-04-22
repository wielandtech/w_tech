import os

from django.core.files import File

from actions.utils import create_action
from .models import Profile
from .utils import get_random_lego_image_file


def create_profile(strategy, details, user=None, *args, **kwargs):
    if user and not hasattr(user, 'profile'):
        # Create the user profile
        profile = Profile(user=user)

        # Assign random default profile image
        lego_img_path = get_random_lego_image_file()
        if lego_img_path:
            with open(lego_img_path, 'rb') as f:
                profile.photo.save(os.path.basename(lego_img_path), File(f), save=False)

        profile.save()
        create_action(user, 'has signed in for the first time.')
    return {'user': user}
