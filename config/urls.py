"""
URL configuration for Product Statistics Service.
"""
from django.urls import include, path

urlpatterns = [
    path('api/', include('products.urls')),
]
