# Appsmith Integration

The backend is designed as an API-first service so that multiple clients can consume it.

The planned Appsmith dashboard is one such client.

## Planned Structure

```text
                        Contract Clause Reviewer API
                                   |
                 +-----------------+-----------------+
                 |                                   |
                 v                                   v
        Application Client                    Appsmith Dashboard
```

The Appsmith dashboard should not duplicate business rules.

It should primarily:

- authenticate the user
- submit analysis requests
- poll analysis status
- display clause findings
- display risk levels
- trigger report generation
- download generated reports
- provide administrative views where authorized

## Importing the Dashboard

When the dashboard export is added to the repository, it should live under:

```text
appsmith/
```

For example:

```text
appsmith/
└── contract-clause-reviewer.json
```

The exact exported filename may differ.

After importing the export into Appsmith:

1. create or update the REST API datasource
2. configure the API base URL
3. configure authentication requests
4. map the analysis endpoints
5. verify that protected requests send the access token
6. verify the analysis polling workflow
7. verify report generation/download

## Suggested API Flow

```text
Login
  |
  v
Access Token
  |
  v
POST /api/v1/analysis/analyze
  |
  v
Celery Task ID
  |
  v
GET analysis status
  |
  v
Completed Analysis
  |
  +--> display risk / clauses
  |
  v
POST /api/v1/reports/{analysis_id}
  |
  v
Report Task ID
  |
  v
GET report status
  |
  v
Download PDF
```

## Why Appsmith Is Useful Here

The Appsmith dashboard is not intended to replace the application's architecture.

It demonstrates an important property of the backend:

> presentation can change without moving business logic into the presentation layer.

The same API can therefore support a coded frontend, an Appsmith dashboard, or another client without duplicating analysis, authorization, persistence and background-processing logic.

## Repository Layout

Once the dashboard is committed, the repository can use:

```text
appsmith/
└── <exported dashboard>.json
```

The README should then link directly to the export and include a screenshot of the finished dashboard alongside the generated report screenshot.
