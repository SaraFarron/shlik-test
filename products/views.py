"""
API Views for Product Statistics Service.
"""
import logging
from decimal import Decimal

from django.core.cache import cache
from django_filters import rest_framework as filters
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Product
from products.serializers import CategoryAvgPriceSerializer, ProductSerializer
from products.services.importer import calculate_avg_price_by_category

logger = logging.getLogger('products')

# Cache timeout in seconds (5 minutes)
CACHE_TIMEOUT = 60 * 5


class ProductFilter(filters.FilterSet):
    """
    Filter for Product list endpoint.
    Supports category exact match and price range filtering.
    """
    category = filters.CharFilter(field_name='category', lookup_expr='iexact')
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')
    
    class Meta:
        model = Product
        fields = ['category', 'price_min', 'price_max']


class ProductListView(generics.ListAPIView):
    """
    GET /api/items
    
    List products with filtering and pagination.
    
    Query Parameters:
    - category: Filter by category (case-insensitive)
    - price_min: Minimum price filter
    - price_max: Maximum price filter
    - page: Page number for pagination
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    ordering_fields = ['name', 'price', 'updated_at', 'category']
    ordering = ['-updated_at']


class AvgPriceByCategoryView(APIView):
    """
    GET /api/stats/avg-price-by-category
    
    Returns average price per category.
    Results are cached for performance.
    """
    
    def get(self, request):
        """
        Get average price by category with Redis caching.
        """
        cache_key = 'avg_price_by_category'
        
        # Try to get from cache
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            logger.debug("Returning cached avg price by category")
            return Response({
                'data': cached_result,
                'cached': True
            })
        
        # Calculate using Pandas
        logger.info("Calculating avg price by category")
        df = calculate_avg_price_by_category()
        
        # Convert DataFrame to list of dicts
        result = df.to_dict('records')
        
        # Convert avg_price to Decimal for proper serialization
        for item in result:
            item['avg_price'] = Decimal(str(item['avg_price'])).quantize(Decimal('0.01'))
        
        # Validate with serializer
        serializer = CategoryAvgPriceSerializer(data=result, many=True)
        serializer.is_valid(raise_exception=True)
        
        # Cache the result
        cache.set(cache_key, serializer.data, CACHE_TIMEOUT)
        logger.info(f"Cached avg price by category for {CACHE_TIMEOUT}s")
        
        return Response({
            'data': serializer.data,
            'cached': False
        })


class HealthCheckView(APIView):
    """
    GET /api/health
    
    Simple health check endpoint.
    """
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'service': 'product-statistics-api'
        }, status=status.HTTP_200_OK)
