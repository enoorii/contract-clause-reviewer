# Testing Strategy

The repository separates unit and integration tests.

```text
tests/
├── conftest.py
├── unit/
│   ├── core/
│   └── services/
└── integration/
    ├── api/
    └── middleware/
```

## Unit Tests

Unit tests focus on application logic without requiring the complete runtime stack.

Examples include:

- security functions
- token operations
- service workflows
- validation behavior
- filtering logic

Unit tests should use mocks/fakes when the behavior being tested does not require a real PostgreSQL or Redis implementation.

## Integration Tests

Integration tests exercise multiple application components together.

The repository groups them into:

```text
integration/api
integration/middleware
```

Typical candidates include:

- authentication endpoints
- analysis endpoints
- report endpoints
- user endpoints
- rate-limiting middleware/dependencies
- request logging behavior

## Test Infrastructure

The test environment is designed so the majority of tests can run without starting the production Docker stack.

Current test substitutes include:

### py-pglite

Used for PostgreSQL-compatible test database execution.

### fakeredis

Used to test Redis-dependent behavior without requiring a live Redis server.

### pytest-asyncio

Configured with automatic async test discovery/execution through:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

## Environment Separation

The repository has separate environment templates:

```text
.env.example
.env.test.example
```

The test environment can therefore use different database and Redis settings from development.

## Running Tests

Full suite:

```bash
ENV_FILE=.env.test uv run pytest
```

Verbose:

```bash
ENV_FILE=.env.test uv run pytest -v
```

Specific file:

```bash
ENV_FILE=.env.test uv run pytest tests/integration/api/test_auth.py -v
```

By expression:

```bash
ENV_FILE=.env.test uv run pytest -k "login"
```

## Testing Dependencies

The development dependency group includes:

- pytest
- pytest-asyncio
- fakeredis
- py-pglite
- freezegun
- httpx2
- IPython/ipykernel for development and investigation

## Fixture Strategy

Shared test configuration belongs in `tests/conftest.py`.

Use shared fixtures for infrastructure that is common across tests, such as:

- test database session
- test application
- HTTP client
- Redis test client
- authenticated test users

Do not force every test to use every fixture.

For example, a rate-limiting test should be able to exercise the real rate-limiting dependency rather than automatically bypassing it through a generic authentication fixture.

## Mocking Principles

The goal is to replace external boundaries, not the code being tested.

Good examples:

```text
service test
  |
  +--> fake repository
  +--> fake LLM
  |
  v
real service logic
```

Less useful:

```text
service test
  |
  v
mock(service_function)
```

The second approach can make tests pass without testing the real workflow.

## Testing the LLM Boundary

LLM requests should generally not hit the real provider during automated tests.

Instead, tests should provide deterministic LLM responses that match the `LegalDocumentAnalysis` schema.

The schema itself becomes an important contract:

```text
LLM response
      |
      v
JSON extraction
      |
      v
Pydantic validation
      |
      v
LegalDocumentAnalysis
```

Tests can therefore verify malformed JSON, invalid fields and valid structured responses.

## What to Test First

For highest portfolio value, prioritize:

1. authentication and refresh-token rotation
2. authorization / admin-only routes
3. analysis queueing
4. analysis persistence
5. rate limiting
6. report generation task behavior
7. repository edge cases
8. failure and retry scenarios

These tests demonstrate engineering maturity more clearly than large numbers of shallow CRUD tests.
