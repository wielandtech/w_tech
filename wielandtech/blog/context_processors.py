from .forms import SearchForm
from .models import Post

def search_form(request):
    return {'form': SearchForm()}

def blog_context(request):
    latest_posts = Post.published.all()[:5]
    return {'latest_posts': latest_posts}
