from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'account'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('edit/', views.edit, name='edit'),
    path('register/', views.register, name='register'),
]