import logging

from celery import shared_task
from django.core.cache import cache

from products.services.importer import ProductImporter, ProductImportError

logger = logging.getLogger('products')


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='products.tasks.import_products_task'
)
def import_products_task(self, source_url: str | None = None):
    """
    Celery task to import products from CSV source.
    Includes retry logic and cache invalidation.
    """
    logger.info(f"Starting import task (attempt {self.request.retries + 1})")
    
    try:
        importer = ProductImporter(source_url=source_url)
        stats = importer.import_products()
        
        # Invalidate stats cache after successful import
        cache.delete('avg_price_by_category')
        logger.info("Cache invalidated after import")
        
        return stats
        
    except ProductImportError as e:
        logger.error(f"Import task failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in import task: {e}")
        raise
