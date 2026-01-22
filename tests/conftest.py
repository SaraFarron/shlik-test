import os
from decimal import Decimal

import pytest

# Setup Django settings before importing models
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Configure Django test database - use default pytest-django setup."""
    pass  # Let pytest-django handle the test database


@pytest.fixture(autouse=True)
def clean_db(db):
    """Clean the database before each test that uses db."""
    from products.models import Product
    Product.objects.all().delete()


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for testing."""
    return """name,category,price,updated_at
Laptop Pro 15,Electronics,1299.99,2024-01-15T10:30:00Z
Wireless Mouse,Electronics,29.99,2024-01-15T10:30:00Z
USB-C Hub,Electronics,49.99,2024-01-16T08:00:00Z
Office Chair,Furniture,299.99,2024-01-14T14:20:00Z
Standing Desk,Furniture,549.99,2024-01-14T14:20:00Z
Desk Lamp,Furniture,45.99,2024-01-17T09:15:00Z
Python Cookbook,Books,39.99,2024-01-13T11:00:00Z
Clean Code,Books,44.99,2024-01-13T11:00:00Z"""


@pytest.fixture
def sample_csv_alternate_columns():
    """Sample CSV with alternate column names for normalization testing."""
    return """product_name,type,cost,last_updated
Gaming Keyboard,Electronics,149.99,2024-01-20T12:00:00Z
Ergonomic Mouse,Electronics,79.99,2024-01-20T12:00:00Z"""


@pytest.fixture
def sample_products(db):
    """Create sample products in database for testing."""
    from django.utils import timezone

    from products.models import Product
    
    products = [
        Product(
            name='Laptop Pro 15',
            category='Electronics',
            price=Decimal('1299.99'),
            updated_at=timezone.now(),
            external_id='hash1'
        ),
        Product(
            name='Wireless Mouse',
            category='Electronics',
            price=Decimal('29.99'),
            updated_at=timezone.now(),
            external_id='hash2'
        ),
        Product(
            name='Office Chair',
            category='Furniture',
            price=Decimal('299.99'),
            updated_at=timezone.now(),
            external_id='hash3'
        ),
        Product(
            name='Standing Desk',
            category='Furniture',
            price=Decimal('549.99'),
            updated_at=timezone.now(),
            external_id='hash4'
        ),
        Product(
            name='Python Cookbook',
            category='Books',
            price=Decimal('39.99'),
            updated_at=timezone.now(),
            external_id='hash5'
        ),
    ]
    Product.objects.bulk_create(products)
    return products
