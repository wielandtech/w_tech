import os
import random
from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage

def get_random_lego_image_file():
    static_lego_dir = '/app/static/img/lego-icons/'
    available_images = [
        f for f in os.listdir(static_lego_dir)
        if os.path.isfile(os.path.join(static_lego_dir, f)) and f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    if not available_images:
        return None

    chosen_file = random.choice(available_images)
    full_path = os.path.join(static_lego_dir, chosen_file)
    return full_path
