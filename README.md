# Сервис продуктовой статистики
### Зависимости
- Django 4.2 + Django REST Framework
- PostgreSQL 15
- Redis 7
- Celery 5.3
- Pandas 2.0
- Docker + Docker Compose

### Запуск
```bash
git clone https://github.com/SaraFarron/shlik-test
cd product-statistics-service

docker compose up --build
```

API будет доступно по `http://localhost:8000/api/`

### Тестовый импорт
После запуска сервиса, можно импортировать тестовые данные:

```bash
# Синхронно, из data/sample_products.csv
docker compose exec web python manage.py import_products

# Асинхронно
docker compose exec web python manage.py import_products --async

# Из ссылки
docker compose exec web python manage.py import_products --url https://example.com/data.csv
```

### Тесты
```bash
docker compose exec web pytest
```

### Логи

```bash
docker compose logs -f

docker compose logs -f celery_worker

docker compose logs -f celery_beat
```
### Остановка

```bash
docker compose down

# С удалением базы
docker compose down -v
```

### API ручки

```bash
# Получение всех товаров
curl http://localhost:8000/api/items

# Фильтр по категории
curl "http://localhost:8000/api/items?category=Electronics"

# Фильтр по цене
curl "http://localhost:8000/api/items?price_min=50&price_max=500"

# Фильтр с пагинацией
curl "http://localhost:8000/api/items?category=Electronics&price_max=100&page=1"
```

### Средняя цена, ответ кешируется
```bash
curl http://localhost:8000/api/stats/avg-price-by-category
```
### Обоснование принятых решений

1. REST вместо GraphQL: больше подходит под CRUD и агрегационные операции, бОльше выбор технологий, простота реализации. Также мне кажется, что тестовое выстроено именно под REST.

2. Идемпотентный импорт и генерация ID: товары уникальны по хэшу (SHA-256) `name` + `category`. Это гарантирует уникальность товаров в категориях, поэтому сохраняется идемпотентность и у нас не появляется дублей.

3. Pandas для обработки данных:
- Есть опыт с этим инструментом
- Есть методы для группировок, очистки данных, валидации, парсинга CSV файлов
- Есть визуализация таблиц
- Достаточно быстрый инструмент

4. Redis:
   - Автоматическая инвалидация после каждого импорта
   - Есть готовая батарейка django-redis
   - ttl кеша - 5 минут

5. Нормализация входных данных:
   - `name / product_name / title` → `name`
   - `category / product_category / type` → `category`
   - `price / cost / amount` → `price`
   - `updated_at / last_updated / modified_at` → `updated_at`

6. Расписание Celery Beat: импорт каждые 5 минут (`IMPORT_INTERVAL_MINUTES`).

### Тестовые данные

Файл `data/sample_products.csv`:
```csv
name,category,price,updated_at
Laptop Pro 15,Electronics,1299.99,2024-01-15T10:30:00Z
Wireless Mouse,Electronics,29.99,2024-01-15T10:30:00Z
Office Chair,Furniture,299.99,2024-01-14T14:20:00Z
```

Другие примеры:
```csv
name,category,price,updated_at
Smartphone X,Electronics,899.99,2024-01-16T09:10:00Z
Bluetooth Speaker,Electronics,59.99,2024-01-16T09:10:00Z
Desk Lamp,Furniture,39.99,2024-01-15T18:45:00Z
Notebook A5,Stationery,4.99,2024-01-15T18:45:00Z
Water Bottle,Accessories,14.99,2024-01-14T11:30:00Z
```

```csv
name,category,price,updated_at
Gaming Keyboard,Electronics,149.99,2024-01-17T12:00:00Z
USB-C Hub,Electronics,49.99,2024-01-17T12:00:00Z
Monitor 27",Electronics,399.99,2024-01-16T16:25:00Z
Standing Desk,Furniture,699.99,2024-01-16T16:25:00Z
Desk Organizer,Office,19.99,2024-01-15T09:40:00Z
Headphones,Electronics,199.99,2024-01-15T09:40:00Z
```

```csv
name,category,price,updated_at
Coffee Maker,Kitchen,89.99,2024-01-18T08:15:00Z
Electric Kettle,Kitchen,39.99,2024-01-18T08:15:00Z
Blender,Kitchen,129.99,2024-01-17T14:50:00Z
Toaster,Kitchen,49.99,2024-01-17T14:50:00Z
Cutting Board,Kitchen,24.99,2024-01-16T10:05:00Z
```

### Логи импорта

```
[2026-01-22 08:40:00,002: INFO/MainProcess] Task products.tasks.import_products_task[713f053b-bdef-4e16-bc47-12d0c21d9246] received
INFO 2026-01-22 08:40:00,003 tasks Starting import task (attempt 1)
[2026-01-22 08:40:00,003: INFO/ForkPoolWorker-16] Starting import task (attempt 1)
INFO 2026-01-22 08:40:00,010 importer Starting product import...
[2026-01-22 08:40:00,010: INFO/ForkPoolWorker-16] Starting product import...
INFO 2026-01-22 08:40:00,010 importer Using local fallback: /app/data/sample_products.csv
[2026-01-22 08:40:00,010: INFO/ForkPoolWorker-16] Using local fallback: /app/data/sample_products.csv
INFO 2026-01-22 08:40:00,012 importer Fetched 21 rows from source
[2026-01-22 08:40:00,012: INFO/ForkPoolWorker-16] Fetched 21 rows from source
INFO 2026-01-22 08:40:00,017 importer After cleaning: 18 valid rows
[2026-01-22 08:40:00,017: INFO/ForkPoolWorker-16] After cleaning: 18 valid rows
INFO 2026-01-22 08:40:00,031 importer Created 8 new products
[2026-01-22 08:40:00,031: INFO/ForkPoolWorker-16] Created 8 new products
INFO 2026-01-22 08:40:00,037 importer Updated 10 existing products
[2026-01-22 08:40:00,037: INFO/ForkPoolWorker-16] Updated 10 existing products
INFO 2026-01-22 08:40:00,037 importer Import completed: {'created': 8, 'updated': 10, 'skipped': 0, 'errors': 0, 'total_processed': 18}
[2026-01-22 08:40:00,037: INFO/ForkPoolWorker-16] Import completed: {'created': 8, 'updated': 10, 'skipped': 0, 'errors': 0, 'total_processed': 18}
INFO 2026-01-22 08:40:00,039 tasks Cache invalidated after import
[2026-01-22 08:40:00,039: INFO/ForkPoolWorker-16] Cache invalidated after import
[2026-01-22 08:40:00,040: INFO/ForkPoolWorker-16] Task products.tasks.import_products_task[713f053b-bdef-4e16-bc47-12d0c21d9246] succeeded in 0.037440037936903536s: {'created': 8, 'updated': 10, 'skipped': 0, 'errors': 0, 'total_processed': 18}
```

```
Starting synchronous import...
INFO 2026-01-22 08:53:10,350 importer Starting product import...
INFO 2026-01-22 08:53:10,351 importer Fetching data from URL: https://pastebin.com/raw/URQvBWRf
INFO 2026-01-22 08:53:11,424 importer Fetched 26 rows from source
INFO 2026-01-22 08:53:11,433 importer After cleaning: 22 valid rows
INFO 2026-01-22 08:53:11,451 importer Created 22 new products
INFO 2026-01-22 08:53:11,451 importer Import completed: {'created': 22, 'updated': 0, 'skipped': 0, 'errors': 0, 'total_processed': 22}
```
