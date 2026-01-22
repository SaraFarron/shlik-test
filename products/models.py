from django.db import models


class Product(models.Model):
    """
    Product model with normalized fields.
    Uses external_id for idempotent imports.
    """
    name = models.CharField(max_length=255, db_index=True)
    category = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    updated_at = models.DateTimeField()
    
    # External identifier for idempotent imports (hash of name + category)
    external_id = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Internal timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['category', 'price']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category}) - ${self.price}"
