from django.core.management.base import BaseCommand, CommandError

from products.services.importer import ProductImporter, ProductImportError


class Command(BaseCommand):
    help = 'Import products from CSV source (URL or local fallback)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='Optional URL to fetch CSV from (overrides settings)',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            dest='run_async',
            help='Run import as Celery task',
        )

    def handle(self, *args, **options):
        source_url = options.get('url')
        run_async = options.get('run_async', False)

        if run_async:
            from products.tasks import import_products_task
            self.stdout.write('Queuing import task...')
            task = import_products_task.delay(source_url=source_url)
            self.stdout.write(
                self.style.SUCCESS(f'Import task queued: {task.id}')
            )
            return

        self.stdout.write('Starting synchronous import...')
        
        try:
            importer = ProductImporter(source_url=source_url)
            stats = importer.import_products()
            
            self.stdout.write(self.style.SUCCESS('Import completed successfully!'))
            self.stdout.write(f"  Created: {stats['created']}")
            self.stdout.write(f"  Updated: {stats['updated']}")
            self.stdout.write(f"  Errors: {stats['errors']}")
            self.stdout.write(f"  Total processed: {stats['total_processed']}")
            
        except ProductImportError as e:
            raise CommandError(f'Import failed: {e}')
