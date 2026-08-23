## Testing Setup Guide

### Directory Structure

```
contract-clause-reviewer/
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

- `.env`: main env file, fill your openai api. To create it use

```bash
cp .env.example .env
```

- `.env.test`: used for development. use `docker-compose.test.yaml` with it.

## Commands Reference

| Command                                                                                    | Description                                                                                |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ |
| `ENV_FILE=.env.test docker-compose -f docker-compose.test.yaml --env-file .env.test up -d` | Start test services                                                                        |
| `ENV_FILE=.env.test uv run pytest`                                                         | Run tests (doesn't require any docker container running, they use py-pglite and fakeredis) |
| `ENV_FILE=.env.test uv run pytest tests/test_api.py -v`                                    | Run specific test file with verbose output                                                 |
| `ENV_FILE=.env.test uv run pytest -k "test_login"`                                         | Run tests matching pattern                                                                 |
| `ENV_FILE=.env.test uv run pytest --cov=app`                                               | Run tests with coverage report                                                             |
| `docker-compose -f docker-compose.test.yaml down -v`                                       | Stop test services and clean up                                                            |
| `docker-compose -f docker-compose.test.yaml logs -f`                                       | View test service logs                                                                     |
| `uv run granian --interface asgi app.main:app --host 0.0.0.0 --port 8000`                  | Run application in development mode                                                        |
| `uv run python -m pytest`                                                                  | Run tests (doesn't require any docker container running, they use py-pglite and fakeredis) |

## Environment Variables Summary

| Variable                  | Purpose                                                                                                                                    |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `ENV_FILE=.env`           | Use development environment (default)                                                                                                      |
| `ENV_FILE=.env.test`      | Use test environment (you should run web server with same `.env.test` file and then you can do manual integration tests from openapi docs) |
| `POSTGRES_HOST=localhost` | Connect to PostgreSQL on host (for app)                                                                                                    |
| `POSTGRES_PORT=5433`      | Use test PostgreSQL port                                                                                                                   |
| `REDIS_PORT=6380`         | Use test Redis port                                                                                                                        |

## Quick Start

Make sure the following tools are installed:

- uv
- Docker

```bash
# 1. Clone repository
git clone <your-repo>
cd <project>

# 2. Setup development environment
uv sync

# 3. Start development services
docker compose up -d --build
```

You will see openapi docs at http://localhost:9000/
Authenticate with admin username and password from `.env` file. You should change your password using the specified endpoint to be able to use and test other endpoints.

## Regular Commands For Dev/Test

```bash
# Prepare redis and postgresql instances and run migrations
docker compose -f docker-compose.test.yaml --env-file .env.test up -d
ENV_FILE=.env.test uv run alembic upgrade head

# terminal 1: run celery worker
ENV_FILE=.env.test uv run celery -A app.core.celery:celery_app worker --loglevel=info -Q analysis

# terminal 2: run granian server
ENV_FILE=.env.test uv run granian --interface asgi app.main:app --host 0.0.0.0 --port 8000
# Or if you want to change code and need hot reload
# ENV_FILE=.env.test uv run granian -reload --interface asgi app.main:app --host 0.0.0.0 --port 8000
```
