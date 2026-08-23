# Architecture

Contract Clause Reviewer uses a pragmatic layered architecture.

The goal is not to implement every abstraction associated with Clean Architecture. The goal is to create clear boundaries so that HTTP, business workflows, persistence and infrastructure concerns can evolve independently.

## Layers

```text
API
 |
 v
Services
 |
 v
Repositories
 |
 v
Database
```

Cross-cutting and external concerns are separated:

```text
Core
Infrastructure
Middleware
Tasks
```

## API Layer

Located in `app/api/`.

Responsibilities:

- define HTTP routes
- validate request input through schemas
- translate service errors into HTTP responses
- compose FastAPI dependencies
- apply authentication and rate-limit dependencies
- return response models

Routes should not contain database query construction or long-running business workflows.

## Service Layer

Located in `app/services/`.

Responsibilities:

- implement application workflows
- coordinate repositories
- decide when background tasks should be queued
- implement authentication workflows
- orchestrate analysis and report generation
- enforce application-level invariants

Example:

```text
POST /analysis/analyze
        |
        v
API route
        |
        v
queue_analysis_task()
        |
        v
Celery task
```

The route does not know how the analysis is performed.

## Repository Layer

Located in `app/repositories/`.

Repositories expose database capabilities such as:

```text
get user
create user
get analysis
list analyses
get refresh token
revoke refresh token
```

The service layer decides what operation should happen. The repository layer decides how the required database operation is performed.

This keeps SQL/ORM details out of application workflows.

## Models and Schemas

### Models

`app/models/` contains SQLModel persistence models.

### Schemas

`app/schemas/` contains Pydantic models used for API contracts and data validation.

Keeping persistence models and API schemas separate prevents the database representation from becoming the public API contract.

## Core

`app/core/` contains application-wide primitives:

- configuration
- security
- Celery configuration
- enums
- exceptions
- filters
- shared utilities

The core layer is allowed to be consumed by other layers because these components are application-wide concerns rather than business workflows.

## Infrastructure

`app/infrastructure/` contains concrete external integrations.

Current integrations include:

```text
Redis
OpenAI-compatible LLM
file storage
logging
```

Infrastructure code is kept outside the service layer so services can focus on application workflows.

## Tasks

`app/tasks/` contains Celery task entry points.

Tasks provide the worker boundary for long-running or blocking operations:

```text
document_tasks.py
report_tasks.py
cleanup_tasks.py
```

The task layer is intentionally thin. It invokes application services or infrastructure components and persists task results.

## Middleware

`app/middleware/` contains request-level cross-cutting behavior:

- request logging
- global rate limiting

Endpoint-specific rate limiting is implemented as FastAPI dependencies under the Redis infrastructure package.

## Dependency Direction

The practical dependency direction is:

```text
API
 |
 v
Services
 |
 v
Repositories
 |
 v
Models / Database
```

With infrastructure dependencies entering where needed:

```text
API ---------> Infrastructure (Redis / logging)
Services ----> Infrastructure (LLM / storage / logging)
Tasks -------> Services / Infrastructure / DB
Core --------> application-wide shared primitives
```

The architecture intentionally avoids making every dependency pass through an abstract interface. That would add indirection without much value for this project.

The main decoupling mechanisms are:

1. service/repository separation
2. FastAPI dependency injection
3. infrastructure modules for external systems
4. Pydantic schemas at boundaries
5. Celery as a process boundary for long-running work

## Dependency Injection

FastAPI dependencies are used for:

- database sessions
- current-user resolution
- active-user checks
- admin authorization
- rate limiting
- Redis clients

For example:

```python
async def endpoint(
    user: ActiveUserAnalysisRateLimit,
    analysis_data: AnalysisCreate,
):
    ...
```

The endpoint receives an already-authenticated and rate-limited user rather than manually implementing those concerns.

## Why Not a More Abstract Architecture?

A common failure mode in portfolio projects is adding interfaces, factories and adapter classes simply to demonstrate architecture.

This project deliberately avoids that.

A new abstraction is worthwhile when it:

- isolates an external dependency
- makes a testing seam clearer
- prevents a layer from knowing too much
- allows a realistic implementation to change

Otherwise, a direct function dependency is preferred.

## Async Strategy

The web layer is async-first:

- FastAPI endpoints use `async def`
- database access uses `asyncpg`
- Redis access uses async Redis clients
- LLM access uses `AsyncOpenAI`

Celery workers intentionally operate as synchronous task processes.

The document analysis task creates/uses the asynchronous LLM service inside the worker process and bridges into it with `asyncio.run()`.

This is a deliberate boundary:

```text
Async HTTP application
          |
          v
       Celery
          |
          v
Isolated worker process
```

It prevents long-running operations from consuming web-server execution time.

## Scaling Model

The architecture allows the API and worker tiers to scale separately.

For example:

```text
                 +----------+
Clients -------->| API x N  |
                 +----------+
                      |
                      v
                    Redis
                      |
             +--------+--------+
             |        |        |
             v        v        v
          Worker   Worker   Worker
```

Increasing Celery worker concurrency increases analysis/report throughput without changing the API process count.

Likewise, API replicas can be scaled independently when HTTP traffic grows.

## Key Design Trade-offs

### PostgreSQL for durable state

PostgreSQL is used for users, analyses, clauses and refresh tokens because these are durable application records.

### Redis for ephemeral coordination

Redis is appropriate for:

- Celery messaging
- task result state
- rate limiting

The application does not treat Redis as the system of record.

### Local report storage

Reports are currently written to a shared filesystem volume.

This is simple for a Docker Compose deployment. A production deployment with multiple hosts would likely use object storage such as S3-compatible storage.

### No frontend coupling

The backend exposes API contracts rather than embedding a specific UI into the architecture. This is what allows the planned Appsmith dashboard to become another client without changing the service layer.
