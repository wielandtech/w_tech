import redis
from actions.utils import create_action
from common.decorators import ajax_required
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.core.files.uploadhandler import TemporaryFileUploadHandler
from .forms import ImageCreateForm, ImageUploadForm
from .models import Image
import logging

logger = logging.getLogger(__name__)

# connect to redis with error handling
try:
    r = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_KEY if hasattr(settings, 'REDIS_KEY') else None,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )
    # Test the connection
    r.ping()
except redis.ConnectionError as e:
    logger.error(f"Redis connection error: {e}")
    r = None
except Exception as e:
    logger.error(f"Redis error: {e}")
    r = None

@login_required
def image_create(request):
    if request.method == 'POST':
        # form is sent
        form = ImageCreateForm(data=request.POST)
        if form.is_valid():
            # form data is valid
            cd = form.cleaned_data
            new_item = form.save(commit=False)
            # assign current user to the item
            new_item.user = request.user
            new_item.save()
            create_action(request.user, 'shared image', new_item)
            messages.success(request, 'Image added successfully')
            # redirect to new created item detail view
            return redirect(new_item.get_absolute_url())
    else:
        # build form with data provided by the bookmarklet via GET
        form = ImageCreateForm(data=request.GET)
    return render(request,
                  'images/image/create.html',
                  {'section': 'images',
                   'form': form})

def image_detail(request, id, slug):
    image = get_object_or_404(Image, id=id, slug=slug)
    # increment total image views by 1
    total_views = 0
    if r is not None:
        try:
            total_views = r.incr(f'image:{image.id}:views')
        except redis.RedisError as e:
            logger.error(f"Redis error in image_detail: {e}")
    return render(request,
              'images/image/detail.html',
              {'section': 'images',
               'image': image,
               'total_views': total_views})

@ajax_required
@login_required
@require_POST
def image_like(request):
    image_id = request.POST.get('id')
    action = request.POST.get('action')
    if image_id and action:
        try:
            image = Image.objects.get(id=image_id)
            if action == 'like':
                image.users_like.add(request.user)
                create_action(request.user, 'likes', image)
            else:
                image.users_like.remove(request.user)
            return JsonResponse({'status':'ok'})
        except:
            pass
    return JsonResponse({'status': 'error'})

def image_list(request):
    images = Image.objects.order_by('-total_likes')
    paginator = Paginator(images, 8)
    page = request.GET.get('page')
    try:
        images = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        images = paginator.page(1)
    except EmptyPage:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # If the request is AJAX and the page is out of range
            # return an empty page
            return HttpResponse('')
        # If page is out of range deliver last page of results
        images = paginator.page(paginator.num_pages)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request,
                      'images/image/list_ajax.html',
                      {'section': 'images', 'images': images})
    return render(request,
                  'images/image/list.html',
                  {'section': 'images', 'images': images})

@login_required
def image_upload(request):
    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            new_item = form.save(commit=False)
            new_item.user = request.user
            new_item.save()
            create_action(request.user, 'uploaded image', new_item)
            messages.success(request, 'Image uploaded successfully')
            return redirect(new_item.get_absolute_url())
    else:
        form = ImageUploadForm()
    return render(request,
                  'images/image/upload.html',
                  {'section': 'images',
                   'form': form})