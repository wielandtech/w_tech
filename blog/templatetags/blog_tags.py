import markdown

from django import template
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from ..models import Post

register = template.Library()


@register.filter(name='markdown')
def markdown_format(text):
    return mark_safe(markdown.markdown(text))


@register.simple_tag
def truncate_with_read_more(text, word_count, post_url):
    """
    Truncate text and add 'Read More' link only if truncation occurred.
    """
    from django.template.defaultfilters import truncatewords_html
    from django.utils.html import strip_tags
    
    # Process markdown first
    processed_text = markdown.markdown(text)
    
    # Count words in the original text (without HTML tags)
    original_word_count = len(strip_tags(processed_text).split())
    
    # If original text has fewer words than the limit, no truncation needed
    if original_word_count <= word_count:
        return mark_safe(processed_text)
    
    # Truncate the HTML content
    truncated_html = truncatewords_html(processed_text, word_count)
    
    # Add the Read More link
    read_more_link = format_html(
        '{} <a href="{}" class="read-more-link">Read More</a>',
        truncated_html,
        post_url
    )
    
    return read_more_link






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
