"""
DRF Serializers for Product API.
"""
from rest_framework import serializers

from products.models import Product


class ProductSerializer(serializers.ModelSerializer):
    """Serializer for Product model."""
    
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'category',
            'price',
            'updated_at',
            'created_at',
            'modified_at',
        ]
        read_only_fields = fields


class CategoryAvgPriceSerializer(serializers.Serializer):
    """Serializer for average price by category."""
    category = serializers.CharField()
    avg_price = serializers.DecimalField(max_digits=10, decimal_places=2)
