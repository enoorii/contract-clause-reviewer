# Appsmith Integration

The backend is designed as an API-first service so that multiple clients can consume it.
The Appsmith dashboard is one such client.

## Structure

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
The Appsmith dashboard is available in following path:
```text
appsmith/
└── Contract Clause Reviewer.json
```

## API Flow

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
```

## Why Appsmith Is Useful Here

The Appsmith dashboard is not intended to replace the application's architecture.
It demonstrates an important property of the backend:

> presentation can change without moving business logic into the presentation layer.

The same API can therefore support a coded frontend, an Appsmith dashboard, or another client without duplicating analysis, authorization, persistence and background-processing logic.

## Technical Notes
Appsmith dashboard impelements following functionalities.

1. Custom JWT based RBAC authentication. With automatic refresh and error handling behind the scene
2. Automatic redirects
3. Centeralized API Client that provides a single interfance for messages, error handling, logic check and redirects
4. Multi-Page setup, each page uses an specific JS object for exclusive functionalities
5. Shared logic from first 3 point of technical notes between all pages
6. Appsmith native functionalities are used to implement lists within lists logic to represent analysis and their sub-items in a graceful manner

## Reflections
I used some components from one of my previous [projects](https://github.com/enoorii/JinjaTask) and Appsmith allows to copy widgets (or group of widgets) between projects and modify them for new project needs. That being said Appsmith cannot provide the same reusability as coded UIs.
I tried to design the structure in a way that implementations become decoupled from project logic so they can be reused later. But that essentially made me to use code extensively. (essentially covering all queries by a shared API client which is called through JS objects)
Nature of Appsmith as a low/no code app builder make the experience of using code less than satisfactory. At this point maybe using a simple coded solution (ex: svelte or htmx+alpinejs) be a better solution as AI can be a lot more helpful and if well structured many of components can be reused later.