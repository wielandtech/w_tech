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
    Truncate HTML text to specified word count and add a 'Read More' link.
    Uses Django's truncatewords_html as base and adds the Read More link.
    """
    from django.template.defaultfilters import truncatewords_html
    
    # Process markdown first
    processed_text = markdown.markdown(text)
    
    # Then truncate the HTML content
    truncated_html = truncatewords_html(processed_text, word_count)
    
    # Check if truncation actually occurred by comparing lengths
    # If the truncated version is the same as original, no truncation happened
    if len(truncated_html) >= len(processed_text):
        return mark_safe(processed_text)
    
    # Add the Read More link
    read_more_link = format_html(
        '{} <a href="{}" class="read-more-link">Read More</a>',
        truncated_html,
        post_url
    )
    
    return mark_safe(read_more_link)


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
