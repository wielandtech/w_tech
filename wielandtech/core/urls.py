from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='core_home'),  # The route for core/index.html
]