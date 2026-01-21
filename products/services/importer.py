"""
Product import service using Pandas for data processing.
Handles CSV import from URL or local fallback with idempotent operations.
"""
import hashlib
import logging
from datetime import timezone as dt_timezone
from decimal import Decimal
from io import StringIO
from typing import Optional

import pandas as pd
import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from products.models import Product

logger = logging.getLogger('products')


class ProductImportError(Exception):
    """Custom exception for import errors."""
    pass


class ProductImporter:
    """
    Service class for importing products from CSV sources.
    Implements idempotent import using external_id hashing.
    """
    
    # Column mapping for normalization (source_column: target_column)
    COLUMN_MAPPING = {
        'name': 'name',
        'product_name': 'name',
        'title': 'name',
        'category': 'category',
        'product_category': 'category',
        'type': 'category',
        'price': 'price',
        'cost': 'price',
        'amount': 'price',
        'updated_at': 'updated_at',
        'last_updated': 'updated_at',
        'modified_at': 'updated_at',
        'date': 'updated_at',
    }
    
    REQUIRED_COLUMNS = {'name', 'category', 'price', 'updated_at'}

    def __init__(self, source_url: Optional[str] = None):
        """
        Initialize importer with optional source URL.
        Falls back to local file if URL is not provided or fails.
        """
        self.source_url = source_url or settings.IMPORT_SOURCE_URL
        self.fallback_path = settings.IMPORT_FALLBACK_PATH

    def generate_external_id(self, name: str, category: str) -> str:
        """
        Generate a unique external ID for idempotent imports.
        Uses SHA-256 hash of normalized name + category.
        """
        normalized = f"{name.strip().lower()}|{category.strip().lower()}"
        return hashlib.sha256(normalized.encode()).hexdigest()

    def fetch_data(self) -> pd.DataFrame:
        """
        Fetch CSV data from URL or fallback to local file.
        Returns a pandas DataFrame.
        """
        # Try fetching from URL first
        if self.source_url:
            try:
                logger.info(f"Fetching data from URL: {self.source_url}")
                response = requests.get(self.source_url, timeout=30)
                response.raise_for_status()
                return pd.read_csv(StringIO(response.text))
            except requests.RequestException as e:
                logger.warning(f"Failed to fetch from URL: {e}. Using fallback.")
        
        # Fallback to local file
        if self.fallback_path.exists():
            logger.info(f"Using local fallback: {self.fallback_path}")
            return pd.read_csv(self.fallback_path)
        
        raise ProductImportError("No data source available")

    def normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize DataFrame columns to match our schema.
        Handles different column naming conventions from various sources.
        """
        # Convert column names to lowercase for matching
        df.columns = df.columns.str.lower().str.strip()
        
        # Rename columns based on mapping
        rename_map = {}
        for source_col, target_col in self.COLUMN_MAPPING.items():
            if source_col in df.columns and target_col not in rename_map.values():
                rename_map[source_col] = target_col
        
        df = df.rename(columns=rename_map)
        
        # Validate required columns
        missing_cols = self.REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            raise ProductImportError(f"Missing required columns: {missing_cols}")
        
        # Keep only required columns
        df = df[list(self.REQUIRED_COLUMNS)].copy()
        
        return df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and validate data types.
        """
        # Remove rows with missing values
        initial_count = len(df)
        df = df.dropna(subset=['name', 'category', 'price'])
        dropped_count = initial_count - len(df)
        if dropped_count > 0:
            logger.warning(f"Dropped {dropped_count} rows with missing values")
        
        # Clean string columns
        df['name'] = df['name'].astype(str).str.strip()
        df['category'] = df['category'].astype(str).str.strip()
        
        # Convert price to decimal
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df = df.dropna(subset=['price'])
        df = df[df['price'] > 0]  # Remove invalid prices
        
        # Parse datetime
        df['updated_at'] = pd.to_datetime(df['updated_at'], errors='coerce')
        # Fill missing dates with current time
        df['updated_at'] = df['updated_at'].fillna(pd.Timestamp.now(tz='UTC'))
        
        # Generate external IDs
        df['external_id'] = df.apply(
            lambda row: self.generate_external_id(row['name'], row['category']),
            axis=1
        )
        
        # Remove duplicates based on external_id (keep last)
        df = df.drop_duplicates(subset=['external_id'], keep='last')
        
        return df

    @transaction.atomic
    def import_products(self) -> dict:
        """
        Main import method. Fetches, normalizes, and imports products.
        Returns statistics about the import operation.
        """
        logger.info("Starting product import...")
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'total_processed': 0,
        }
        
        try:
            # Fetch and process data
            df = self.fetch_data()
            logger.info(f"Fetched {len(df)} rows from source")
            
            df = self.normalize_dataframe(df)
            df = self.clean_data(df)
            logger.info(f"After cleaning: {len(df)} valid rows")
            
            # Get existing products by external_id
            existing_ids = set(
                Product.objects.filter(
                    external_id__in=df['external_id'].tolist()
                ).values_list('external_id', flat=True)
            )
            
            products_to_create = []
            products_to_update = []
            
            for _, row in df.iterrows():
                stats['total_processed'] += 1
                
                try:
                    product_data = {
                        'name': row['name'],
                        'category': row['category'],
                        'price': Decimal(str(row['price'])).quantize(Decimal('0.01')),
                        'updated_at': row['updated_at'].to_pydatetime().replace(
                            tzinfo=dt_timezone.utc
                        ) if pd.notna(row['updated_at']) else timezone.now(),
                        'external_id': row['external_id'],
                    }
                    
                    if row['external_id'] in existing_ids:
                        products_to_update.append(product_data)
                    else:
                        products_to_create.append(Product(**product_data))
                        
                except Exception as e:
                    logger.error(f"Error processing row {row['name']}: {e}")
                    stats['errors'] += 1
            
            # Bulk create new products
            if products_to_create:
                Product.objects.bulk_create(products_to_create, ignore_conflicts=True)
                stats['created'] = len(products_to_create)
                logger.info(f"Created {stats['created']} new products")
            
            # Bulk update existing products
            if products_to_update:
                for product_data in products_to_update:
                    Product.objects.filter(
                        external_id=product_data['external_id']
                    ).update(
                        name=product_data['name'],
                        category=product_data['category'],
                        price=product_data['price'],
                        updated_at=product_data['updated_at'],
                    )
                stats['updated'] = len(products_to_update)
                logger.info(f"Updated {stats['updated']} existing products")
            
            logger.info(f"Import completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise ProductImportError(f"Import failed: {e}")


def calculate_avg_price_by_category() -> pd.DataFrame:
    """
    Calculate average price per category using Pandas.
    Returns a DataFrame with category and avg_price columns.
    """
    products = Product.objects.values('category', 'price')
    
    if not products:
        return pd.DataFrame(columns=['category', 'avg_price'])
    
    df = pd.DataFrame(list(products))
    
    # Convert price to float for calculation
    df['price'] = df['price'].astype(float)
    
    # Calculate average price per category
    result = df.groupby('category')['price'].mean().reset_index()
    result.columns = ['category', 'avg_price']
    
    # Round to 2 decimal places
    result['avg_price'] = result['avg_price'].round(2)
    
    return result
