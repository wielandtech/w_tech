from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
import random
import os


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date_of_birth = models.DateField(blank=True, null=True)
    photo = models.ImageField(upload_to='users/%Y/%m/%d/', 
                              blank=True)

    def save(self, *args, **kwargs):
        if not self.photo:
            # Get path to lego-icons directory
            lego_icons_dir = os.path.join(settings.MEDIA_ROOT, 'lego-icons')
            
            # Get list of all files in the directory
            if os.path.exists(lego_icons_dir):
                icon_files = [f for f in os.listdir(lego_icons_dir) 
                              if os.path.isfile(os.path.join(lego_icons_dir, f))]
                
                if icon_files:
                    # Randomly select one icon
                    random_icon = random.choice(icon_files)
                    # Set relative path from MEDIA_ROOT
                    self.photo = os.path.join('lego-icons', random_icon)

        super().save(*args, **kwargs)

    def __str__(self):
        return f'Profile for user {self.user.username}'


class Contact(models.Model):
    user_from = models.ForeignKey('auth.User',
                                  related_name='rel_from_set',
                                  on_delete=models.CASCADE)
    user_to = models.ForeignKey('auth.User',
                                related_name='rel_to_set',
                                on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True,
                                   db_index=True)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'{self.user_from} follows {self.user_to}'


# Add following field to User dynamically
user_model = get_user_model()
user_model.add_to_class('following',
                        models.ManyToManyField('self',
                                               through=Contact,
                                               related_name='followers',
                                               symmetrical=False))
