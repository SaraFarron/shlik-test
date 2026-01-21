# Product Statistics Service

A production-ready Django REST API service for importing and serving product statistics. Features scheduled CSV imports via Celery, Pandas-based data processing, and Redis caching.

## Features

- **Data Import**: Fetch product data from CSV (HTTP/HTTPS URL or local fallback)
- **Data Processing**: Pandas-based normalization and average price calculation
- **REST API**: Filter products by category and price range with pagination
- **Caching**: Redis-backed caching for aggregate statistics
- **Scheduled Tasks**: Celery Beat for automated periodic imports
- **Idempotent Import**: Safe to run multiple times without data duplication

## Tech Stack

- **Framework**: Django 4.2 + Django REST Framework
- **Database**: PostgreSQL 15
- **Cache/Broker**: Redis 7
- **Task Queue**: Celery 5.3
- **Data Processing**: Pandas 2.0
- **Containerization**: Docker + Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Git

### One-Command Startup

```bash
# Clone the repository
git clone https://github.com/your-username/product-statistics-service.git
cd product-statistics-service

# Start all services
docker compose up --build
```

The API will be available at `http://localhost:8000/api/`

### Initial Data Import

After starting the services, trigger the initial import:

```bash
# Option 1: Using management command (synchronous)
docker compose exec web python manage.py import_products

# Option 2: Using Celery task (asynchronous)
docker compose exec web python manage.py import_products --async

# Option 3: From custom URL
docker compose exec web python manage.py import_products --url https://example.com/data.csv
```

## API Endpoints

### List Products

```
GET /api/items
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `category` | string | Filter by category (case-insensitive) |
| `price_min` | decimal | Minimum price filter |
| `price_max` | decimal | Maximum price filter |
| `page` | integer | Page number for pagination |

**Example Requests:**

```bash
# List all products
curl http://localhost:8000/api/items

# Filter by category
curl "http://localhost:8000/api/items?category=Electronics"

# Filter by price range
curl "http://localhost:8000/api/items?price_min=50&price_max=500"

# Combined filters with pagination
curl "http://localhost:8000/api/items?category=Electronics&price_max=100&page=1"
```

**Example Response:**

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Laptop Pro 15",
      "category": "Electronics",
      "price": "1299.99",
      "updated_at": "2024-01-15T10:30:00Z",
      "created_at": "2024-01-20T12:00:00Z",
      "modified_at": "2024-01-20T12:00:00Z"
    }
  ]
}
```

### Average Price by Category (Cached)

```
GET /api/stats/avg-price-by-category
```

**Example Request:**

```bash
curl http://localhost:8000/api/stats/avg-price-by-category
```

**Example Response:**

```json
{
  "data": [
    {"category": "Electronics", "avg_price": "459.99"},
    {"category": "Furniture", "avg_price": "298.66"},
    {"category": "Books", "avg_price": "42.49"},
    {"category": "Kitchen", "avg_price": "109.99"}
  ],
  "cached": false
}
```

### Health Check

```bash
curl http://localhost:8000/api/health
```

## Architecture & Design Decisions

### Project Structure

```
├── config/                 # Django project configuration
│   ├── settings.py        # Main settings with env var support
│   ├── celery.py          # Celery app configuration
│   └── urls.py            # Root URL routing
├── products/              # Main application
│   ├── models.py          # Product model with external_id
│   ├── views.py           # DRF views with filtering
│   ├── serializers.py     # API serializers
│   ├── tasks.py           # Celery tasks
│   ├── services/          # Business logic
│   │   └── importer.py    # Pandas-based import service
│   └── management/        # Django commands
│       └── commands/
│           └── import_products.py
├── tests/                 # Pytest test suite
└── data/                  # Sample data for fallback
```

### Key Design Decisions

1. **REST over GraphQL**: Chosen for simplicity, better HTTP caching support, and wider tooling ecosystem. The requirements are straightforward CRUD + aggregation which REST handles elegantly.

2. **Idempotent Import via External ID**: Products are identified by a SHA-256 hash of `name + category`. This ensures:
   - Running import multiple times is safe
   - Updates are handled correctly
   - No duplicate entries

3. **Pandas for Data Processing**: Used for:
   - CSV parsing and normalization
   - Column name mapping (handles various source formats)
   - Data cleaning and validation
   - Average price calculation with `groupby`

4. **Redis Caching Strategy**:
   - Stats endpoint cached for 5 minutes
   - Cache invalidated automatically after each import
   - Uses django-redis for cache backend

5. **Column Normalization**: The importer handles various column naming conventions:
   - `name` / `product_name` / `title` → `name`
   - `category` / `product_category` / `type` → `category`
   - `price` / `cost` / `amount` → `price`
   - `updated_at` / `last_updated` / `modified_at` → `updated_at`

6. **Celery Beat Schedule**: Configured to run imports every 5 minutes (configurable via `IMPORT_INTERVAL_MINUTES`).

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `0` | Enable debug mode |
| `SECRET_KEY` | (generated) | Django secret key |
| `POSTGRES_DB` | `products_db` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `IMPORT_SOURCE_URL` | (empty) | CSV source URL |
| `IMPORT_INTERVAL_MINUTES` | `5` | Celery Beat interval |

### Sample Data

A fallback CSV file is included at `data/sample_products.csv`:

```csv
name,category,price,updated_at
Laptop Pro 15,Electronics,1299.99,2024-01-15T10:30:00Z
Wireless Mouse,Electronics,29.99,2024-01-15T10:30:00Z
Office Chair,Furniture,299.99,2024-01-14T14:20:00Z
...
```

## Development

### Running Tests

```bash
# Run all tests
docker compose exec web pytest

# Run with coverage
docker compose exec web pytest --cov=products

# Run specific test class
docker compose exec web pytest tests/test_products.py::TestEndpointFiltering
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Celery worker only
docker compose logs -f celery_worker

# Celery beat only
docker compose logs -f celery_beat
```

### Stopping Services

```bash
docker compose down

# Remove volumes (database data)
docker compose down -v
```

## Import Logs

Import operations are logged to the console. Example output:

```
INFO 2024-01-20 12:00:00 importer Starting product import...
INFO 2024-01-20 12:00:01 importer Fetched 10 rows from source
INFO 2024-01-20 12:00:01 importer After cleaning: 10 valid rows
INFO 2024-01-20 12:00:02 importer Created 10 new products
INFO 2024-01-20 12:00:02 importer Import completed: {'created': 10, 'updated': 0, 'errors': 0, 'total_processed': 10}
INFO 2024-01-20 12:00:02 tasks Cache invalidated after import
```

## License

MIT License
