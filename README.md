## Testing Setup Guide

### Directory Structure

```
project-root/
├── .env                    # Development environment
├── .env.test              # Test environment
├── docker-compose.yaml    # Development services
├── docker-compose.test.yaml # Test services
├── app/
│   └── main.py
├── tests/
└── scripts/
    └── test.sh           # Test helper script (optional)
```

### Environment Files

**`.env`** (Development):

```env
# Environment
DEV_MODE=False

# PostgreSQL
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Security
SECRET_KEY=your-secret-key-here
ADMIN_USER=admin
ADMIN_PASS=admin

# Other
DEFAULT_PER_PAGE=10
```

**`.env.test`** (Testing):

```env
# Environment
DEV_MODE=True

# PostgreSQL - Test
POSTGRES_USER=test_user
POSTGRES_PASSWORD=test_password
POSTGRES_DB=test_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5433

# Redis - Test
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_PASSWORD=

# Security
SECRET_KEY=test-secret-key-for-testing-only
ADMIN_USER=admin
ADMIN_PASS=admin

# Other
DEFAULT_PER_PAGE=5
```

### Docker Compose Files

**`docker-compose.yaml`** (Development):

```yaml
services:
  db:
    image: postgres:18-alpine
    container_name: contract_clause_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      POSTGRES_DB: ${POSTGRES_DB:-db}
    ports:
      - "5432:5432"
    networks:
      - task_manager_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-user}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: contract_clause_redis
    ports:
      - "6379:6379"
    networks:
      - task_manager_network
    healthcheck:
      test: ["CMD-SHELL", "redis-cli ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

networks:
  task_manager_network:
    driver: bridge
```

**`docker-compose.test.yaml`** (Testing):

```yaml
services:
  test-db:
    image: postgres:18-alpine
    container_name: contract_clause_test_db
    environment:
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
      POSTGRES_DB: test_db
    ports:
      - "5433:5432" # Different port to avoid conflicts
    networks:
      - test_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_user"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  test-redis:
    image: redis:7-alpine
    container_name: contract_clause_test_redis
    ports:
      - "6380:6379" # Different port to avoid conflicts
    networks:
      - test_network
    healthcheck:
      test: ["CMD-SHELL", "redis-cli ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

networks:
  test_network:
    driver: bridge
```

### Configuration (`config.py`)

```python
import os
from pathlib import Path
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    # Database
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: str = "5432"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None

    # ... other fields ...

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / os.getenv("ENV_FILE", ".env")),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()
```

## Commands Reference

### Development

| Command                                                    | Description                                       |
| ---------------------------------------------------------- | ------------------------------------------------- |
| `docker-compose up -d`                                     | Start development services (PostgreSQL & Redis)   |
| `docker-compose logs -f`                                   | View logs from all services                       |
| `docker-compose down`                                      | Stop development services                         |
| `docker-compose down -v`                                   | Stop services and remove volumes (clean database) |
| `ENV_FILE=.env uv run uvicorn app.main:app --host 0.0.0.0` | Run application in development mode               |
| `uv run pytest`                                            | Run tests (requires test services running)        |

### Testing

| Command                                                                                    | Description                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------ |
| `ENV_FILE=.env.test docker-compose -f docker-compose.test.yaml --env-file .env.test up -d` | Start test services                        |
| `ENV_FILE=.env.test uv run pytest`                                                         | Run all tests with test environment        |
| `ENV_FILE=.env.test uv run pytest tests/test_api.py -v`                                    | Run specific test file with verbose output |
| `ENV_FILE=.env.test uv run pytest -k "test_login"`                                         | Run tests matching pattern                 |
| `ENV_FILE=.env.test uv run pytest --cov=app`                                               | Run tests with coverage report             |
| `docker-compose -f docker-compose.test.yaml down -v`                                       | Stop test services and clean up            |
| `docker-compose -f docker-compose.test.yaml logs -f`                                       | View test service logs                     |

### Quick Test Commands

**One-liner (Full Test Run):**

```bash
# Start services, run tests, clean up
ENV_FILE=.env.test docker-compose -f docker-compose.test.yaml --env-file .env.test up -d && \
ENV_FILE=.env.test uv run pytest && \
docker-compose -f docker-compose.test.yaml down -v
```

**With Coverage:**

```bash
ENV_FILE=.env.test docker-compose -f docker-compose.test.yaml --env-file .env.test up -d && \
ENV_FILE=.env.test uv run pytest --cov=app --cov-report=html && \
docker-compose -f docker-compose.test.yaml down -v
```

**Run Specific Test File:**

```bash
ENV_FILE=.env.test docker-compose -f docker-compose.test.yaml --env-file .env.test up -d && \
ENV_FILE=.env.test uv run pytest tests/test_auth.py -v && \
docker-compose -f docker-compose.test.yaml down -v
```

### Test Helper Script

Create `scripts/test.sh`:

```bash
#!/bin/bash
set -e

export ENV_FILE=.env.test

echo "🚀 Starting test containers..."
docker-compose -f docker-compose.test.yaml --env-file .env.test up -d

echo "⏳ Waiting for services to be ready..."
sleep 3

echo "🧪 Running tests..."
uv run pytest "$@"

TEST_EXIT_CODE=$?

echo "🧹 Cleaning up..."
docker-compose -f docker-compose.test.yaml down -v

exit $TEST_EXIT_CODE
```

Make it executable:

```bash
chmod +x scripts/test.sh
```

Usage:

```bash
./scripts/test.sh                          # Run all tests
./scripts/test.sh -v                       # Verbose output
./scripts/test.sh tests/test_auth.py       # Run specific test file
./scripts/test.sh -k "test_login"          # Run tests matching pattern
./scripts/test.sh --cov=app                # With coverage
```

## Common Issues & Solutions

| Issue                                  | Solution                                                                                |
| -------------------------------------- | --------------------------------------------------------------------------------------- |
| `Address already in use` for port 5432 | Stop any running PostgreSQL on host, or use test environment with different ports       |
| `Connection refused` to database       | Ensure containers are running: `docker-compose ps`                                      |
| Container conflicts                    | Use `docker-compose down -v` to clean up                                                |
| Environment not loading                | Ensure `ENV_FILE` is set: `export ENV_FILE=.env.test`                                   |
| Tests failing after changes            | Rebuild containers: `docker-compose -f docker-compose.test.yaml up -d --force-recreate` |

## Environment Variables Summary

| Variable                  | Purpose                                 |
| ------------------------- | --------------------------------------- |
| `ENV_FILE=.env`           | Use development environment (default)   |
| `ENV_FILE=.env.test`      | Use test environment                    |
| `POSTGRES_HOST=localhost` | Connect to PostgreSQL on host (for app) |
| `POSTGRES_PORT=5433`      | Use test PostgreSQL port                |
| `REDIS_PORT=6380`         | Use test Redis port                     |

## Quick Start

```bash
# 1. Clone repository
git clone <your-repo>
cd <project>

# 2. Setup development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
uv pip install -e ".[dev]"

# 3. Start development services
docker-compose up -d

# 4. Run application
ENV_FILE=.env uv run uvicorn app.main:app --host 0.0.0.0 --reload

# 5. Run tests
./scripts/test.sh
```

## CI/CD Integration

For GitHub Actions, GitLab CI, etc.:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    ENV_FILE=.env.test docker-compose -f docker-compose.test.yaml --env-file .env.test up -d
    ENV_FILE=.env.test pytest --cov=app --cov-report=xml
    docker-compose -f docker-compose.test.yaml down -v
```

---

This setup ensures:

- ✅ Development and test environments are isolated
- ✅ No port conflicts
- ✅ Clean test runs with automatic cleanup
- ✅ Easy to run tests locally or in CI
- ✅ Clear separation of configurations

## Regular Commands For Dev/Test

docker compose -f docker-compose.test.yaml --env-file .env.test up -d

ENV_FILE=.env.test uv run alembic upgrade head

ENV_FILE=.env.test uv run celery -A app.core.celery:celery_app worker --loglevel=info -Q analysis

ENV_FILE=.env.test uv run granian --interface asgi app.main:app --host 0.0.0.0 --port 8000

docker compose -f docker-compose.test.yaml down -v
