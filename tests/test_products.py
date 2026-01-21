"""
Tests for Product Statistics Service.
Covers: parsing/normalization, average price calculation, and endpoint filtering.
"""
from decimal import Decimal
from io import StringIO

import pandas as pd
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from products.services.importer import ProductImporter, calculate_avg_price_by_category

# =============================================================================
# TEST 1: Parsing and Normalization of Input Data
# =============================================================================

class TestDataParsingAndNormalization:
    """Tests for CSV parsing and column normalization."""

    def test_normalize_standard_columns(self, sample_csv_data):
        """Test normalization with standard column names."""
        importer = ProductImporter()
        df = pd.read_csv(StringIO(sample_csv_data))
        
        normalized = importer.normalize_dataframe(df)
        
        # Check all required columns are present
        assert 'name' in normalized.columns
        assert 'category' in normalized.columns
        assert 'price' in normalized.columns
        assert 'updated_at' in normalized.columns
        assert len(normalized) == 8

    def test_normalize_alternate_columns(self, sample_csv_alternate_columns):
        """Test normalization with alternate column names (product_name, type, cost)."""
        importer = ProductImporter()
        df = pd.read_csv(StringIO(sample_csv_alternate_columns))
        
        normalized = importer.normalize_dataframe(df)
        
        # Check columns were properly renamed
        assert 'name' in normalized.columns
        assert 'category' in normalized.columns
        assert 'price' in normalized.columns
        assert 'updated_at' in normalized.columns
        
        # Verify data integrity
        assert normalized.iloc[0]['name'] == 'Gaming Keyboard'
        assert normalized.iloc[0]['category'] == 'Electronics'

    def test_clean_data_removes_invalid_prices(self):
        """Test that invalid prices are removed during cleaning."""
        importer = ProductImporter()
        csv_data = """name,category,price,updated_at
Valid Product,Electronics,99.99,2024-01-15T10:30:00Z
Invalid Price,Electronics,-50,2024-01-15T10:30:00Z
Zero Price,Electronics,0,2024-01-15T10:30:00Z
NaN Price,Electronics,invalid,2024-01-15T10:30:00Z"""
        
        df = pd.read_csv(StringIO(csv_data))
        normalized = importer.normalize_dataframe(df)
        cleaned = importer.clean_data(normalized)
        
        # Only the valid product should remain
        assert len(cleaned) == 1
        assert cleaned.iloc[0]['name'] == 'Valid Product'

    def test_generate_external_id_is_deterministic(self):
        """Test that external ID generation is deterministic for idempotent imports."""
        importer = ProductImporter()
        
        id1 = importer.generate_external_id('Laptop Pro', 'Electronics')
        id2 = importer.generate_external_id('Laptop Pro', 'Electronics')
        id3 = importer.generate_external_id('laptop pro', 'electronics')  # Case insensitive
        
        assert id1 == id2
        assert id1 == id3  # Should be case-insensitive

    def test_generate_external_id_unique_for_different_products(self):
        """Test that different products get different external IDs."""
        importer = ProductImporter()
        
        id1 = importer.generate_external_id('Laptop Pro', 'Electronics')
        id2 = importer.generate_external_id('Laptop Pro', 'Furniture')  # Same name, different category
        id3 = importer.generate_external_id('Desktop Pro', 'Electronics')  # Different name
        
        assert id1 != id2
        assert id1 != id3
        assert id2 != id3


# =============================================================================
# TEST 2: Correct Average Price Calculation
# =============================================================================

class TestAveragePriceCalculation:
    """Tests for Pandas-based average price calculation."""

    @pytest.mark.django_db
    def test_calculate_avg_price_by_category(self, sample_products):
        """Test average price calculation returns correct values."""
        result = calculate_avg_price_by_category()
        
        # Convert to dict for easier assertion
        result_dict = {row['category']: row['avg_price'] for _, row in result.iterrows()}
        
        # Electronics: (1299.99 + 29.99) / 2 = 664.99
        assert result_dict['Electronics'] == pytest.approx(664.99, rel=0.01)
        
        # Furniture: (299.99 + 549.99) / 2 = 424.99
        assert result_dict['Furniture'] == pytest.approx(424.99, rel=0.01)
        
        # Books: 39.99 / 1 = 39.99
        assert result_dict['Books'] == pytest.approx(39.99, rel=0.01)

    @pytest.mark.django_db
    def test_calculate_avg_price_empty_database(self):
        """Test average price calculation with no products."""
        result = calculate_avg_price_by_category()
        
        assert len(result) == 0
        assert 'category' in result.columns
        assert 'avg_price' in result.columns

    @pytest.mark.django_db
    def test_calculate_avg_price_single_category(self, db):
        """Test average price with single category."""
        from django.utils import timezone

        from products.models import Product
        
        Product.objects.create(
            name='Test Product 1',
            category='TestCategory',
            price=Decimal('100.00'),
            updated_at=timezone.now(),
            external_id='test1'
        )
        Product.objects.create(
            name='Test Product 2',
            category='TestCategory',
            price=Decimal('200.00'),
            updated_at=timezone.now(),
            external_id='test2'
        )
        
        result = calculate_avg_price_by_category()
        
        assert len(result) == 1
        assert result.iloc[0]['category'] == 'TestCategory'
        assert result.iloc[0]['avg_price'] == pytest.approx(150.00, rel=0.01)


# =============================================================================
# TEST 3: Endpoint Filtering
# =============================================================================

@pytest.mark.django_db
class TestEndpointFiltering:
    """Tests for API endpoint filtering functionality."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    def test_list_items_no_filter(self, api_client, sample_products):
        """Test listing all items without filters."""
        response = api_client.get('/api/items')
        
        assert response.status_code == 200
        assert 'results' in response.data
        assert len(response.data['results']) == 5

    def test_filter_by_category(self, api_client, sample_products):
        """Test filtering products by category."""
        response = api_client.get('/api/items', {'category': 'Electronics'})
        
        assert response.status_code == 200
        results = response.data['results']
        assert len(results) == 2
        assert all(p['category'] == 'Electronics' for p in results)

    def test_filter_by_category_case_insensitive(self, api_client, sample_products):
        """Test that category filtering is case-insensitive."""
        response = api_client.get('/api/items', {'category': 'electronics'})
        
        assert response.status_code == 200
        results = response.data['results']
        assert len(results) == 2

    def test_filter_by_price_min(self, api_client, sample_products):
        """Test filtering by minimum price."""
        response = api_client.get('/api/items', {'price_min': '100'})
        
        assert response.status_code == 200
        results = response.data['results']
        # Products >= 100: Laptop (1299.99), Office Chair (299.99), Standing Desk (549.99)
        assert len(results) == 3
        assert all(Decimal(p['price']) >= Decimal('100') for p in results)

    def test_filter_by_price_max(self, api_client, sample_products):
        """Test filtering by maximum price."""
        response = api_client.get('/api/items', {'price_max': '50'})
        
        assert response.status_code == 200
        results = response.data['results']
        # Products <= 50: Wireless Mouse (29.99), Python Cookbook (39.99)
        assert len(results) == 2
        assert all(Decimal(p['price']) <= Decimal('50') for p in results)

    def test_filter_by_price_range(self, api_client, sample_products):
        """Test filtering by price range (min and max)."""
        response = api_client.get('/api/items', {'price_min': '30', 'price_max': '300'})
        
        assert response.status_code == 200
        results = response.data['results']
        # Products 30-300: Office Chair (299.99), Python Cookbook (39.99)
        assert len(results) == 2
        for p in results:
            price = Decimal(p['price'])
            assert Decimal('30') <= price <= Decimal('300')

    def test_filter_combined_category_and_price(self, api_client, sample_products):
        """Test combining category and price filters."""
        response = api_client.get('/api/items', {
            'category': 'Electronics',
            'price_max': '100'
        })
        
        assert response.status_code == 200
        results = response.data['results']
        # Only Wireless Mouse (29.99) matches
        assert len(results) == 1
        assert results[0]['name'] == 'Wireless Mouse'

    def test_pagination(self, api_client, sample_products):
        """Test that pagination works correctly."""
        # Request with small page size
        response = api_client.get('/api/items', {'page': '1'})
        
        assert response.status_code == 200
        assert 'count' in response.data
        assert 'next' in response.data
        assert 'previous' in response.data
        assert 'results' in response.data
        assert response.data['count'] == 5

    def test_avg_price_endpoint(self, api_client, sample_products):
        """Test the average price by category endpoint."""
        response = api_client.get('/api/stats/avg-price-by-category')
        
        assert response.status_code == 200
        assert 'data' in response.data
        
        data = {item['category']: Decimal(item['avg_price']) for item in response.data['data']}
        
        assert 'Electronics' in data
        assert 'Furniture' in data
        assert 'Books' in data

    def test_health_endpoint(self, api_client):
        """Test the health check endpoint."""
        response = api_client.get('/api/health')
        
        assert response.status_code == 200
        assert response.data['status'] == 'healthy'


# =============================================================================
# Additional Tests for Idempotent Import
# =============================================================================

@pytest.mark.django_db
class TestIdempotentImport:
    """Tests for idempotent import functionality."""

    def test_import_creates_products(self, db, tmp_path):
        """Test that import creates new products."""
        from products.models import Product
        
        # Create a temporary CSV file
        csv_content = """name,category,price,updated_at
Test Product,Electronics,99.99,2024-01-15T10:30:00Z"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        
        importer = ProductImporter()
        importer.fallback_path = csv_file
        importer.source_url = None
        
        stats = importer.import_products()
        
        assert stats['created'] == 1
        assert Product.objects.count() == 1
        assert Product.objects.first().name == 'Test Product'

    def test_import_is_idempotent(self, db, tmp_path):
        """Test that running import twice doesn't duplicate products."""
        from products.models import Product
        
        csv_content = """name,category,price,updated_at
Test Product,Electronics,99.99,2024-01-15T10:30:00Z"""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)
        
        importer = ProductImporter()
        importer.fallback_path = csv_file
        importer.source_url = None
        
        # First import
        stats1 = importer.import_products()
        assert stats1['created'] == 1
        
        # Second import (should update, not create)
        stats2 = importer.import_products()
        assert stats2['created'] == 0
        assert stats2['updated'] == 1
        
        # Only one product should exist
        assert Product.objects.count() == 1
