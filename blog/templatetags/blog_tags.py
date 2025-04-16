import markdown
import redis

from django import template
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.conf import settings

from ..models import Post

register = template.Library()
redis_instance = redis.Redis(
    host=settings.REDIS_IP,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB
)


@register.filter(name='markdown')
def markdown_format(text):
    return mark_safe(markdown.markdown(text))


@register.simple_tag
def get_most_commented_posts(count=5):
    return Post.published.annotate(total_comments=Count('comments')).order_by('-total_comments')[:count]


@register.inclusion_tag('blog/post/latest_posts.html')
def show_latest_posts(count=5):
    latest_posts = Post.published.order_by('-publish')[:count]
    return {'latest_posts': latest_posts}


@register.simple_tag
def total_posts():
    return Post.published.count()


@register.filter
def user_has_liked(post, user):
    """Check if user has liked a post using Redis"""
    return redis_instance.sismember(f'blog:like:{post.id}', user.id)


@register.filter
def get_likes_count(post):
    """Get the number of likes for a post from Redis"""
    return redis_instance.scard(f'blog:like:{post.id}') or 0
