from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.homepage, name='core_home'),  # The route for core/index.html
    path('contact/', views.contact, name='contact'),
    path('api/metrics/', views.get_netdata_metrics, name='netdata_metrics'),
    path('maintenance/', views.maintenance, name='maintenance'),
]
