from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import User
from taggit.managers import TaggableManager
from django.conf import settings
from core.redis_client import get_redis
import json


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super(PublishedManager, self).get_queryset().filter(status='published')


class Post(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
    
    title = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique_for_date='publish')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    body = models.TextField()
    publish = models.DateTimeField(default=timezone.now)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10,
                              choices=Status.choices,
                              default=Status.DRAFT)
    objects = models.Manager()  # The default manager.
    published = PublishedManager()  # Our custom manager.
    tags = TaggableManager()

    class Meta:
        ordering = ('-publish',)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog:post_detail', args=[self.publish.year, self.publish.month, self.publish.day, self.slug])

    def get_likes(self):
        """Get the total number of likes from Redis"""
        r = get_redis()
        return r.scard(f'blog:post:{self.id}:likes') or 0

    def user_has_liked(self, user_id):
        """Check if a user has liked this post"""
        r = get_redis()
        return r.sismember(f'blog:post:{self.id}:likes', str(user_id))
    
    def toggle_like(self, user):
        """Toggle like status for a user"""
        r = get_redis()
        key = f'blog:post:{self.id}:likes'
        if self.user_has_liked(user.id):
            r.srem(key, str(user.id))
            return False
        else:
            r.sadd(key, str(user.id))
            return True


class Comment(models.Model):
    post = models.ForeignKey(Post, 
                            on_delete=models.CASCADE,
                            related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                            on_delete=models.SET_NULL,
                            null=True,
                            blank=True)
    name = models.CharField(max_length=80)
    email = models.EmailField()
    body = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ('created',)
    
    def save(self, *args, **kwargs):
        if not self.name and self.user:
            self.name = self.user.get_full_name() or self.user.username
        if not self.email and self.user:
            self.email = self.user.email
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'Comment by {self.name} on {self.post}'