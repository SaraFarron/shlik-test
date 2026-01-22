from django.urls import path

from products.views import (
    AvgPriceByCategoryView,
    HealthCheckView,
    ProductListView,
)

urlpatterns = [
    path('items', ProductListView.as_view(), name='product-list'),
    path('stats/avg-price-by-category', AvgPriceByCategoryView.as_view(), name='avg-price-by-category'),
    path('health', HealthCheckView.as_view(), name='health-check'),
]
