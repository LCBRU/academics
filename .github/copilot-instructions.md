# Academics Project - Copilot Instructions

This file gives Copilot (and contributors) high-level guidance about the `academics` Flask project: structure, common tasks, testing, development workflow, and best practices. Use it as a quick reference when creating or editing code in this repository.

## Project overview

- Name: academics
- Tech stack: Python, Flask, SQLAlchemy, Alembic, pytest
- Purpose: Web service and UI for academic records, notifications and data ingestion jobs.
- Key directories:
  - `academics/` - main application package (blueprints, models, services, UI)
  - `alembic/` - database migrations
  - `tests/` - test suite (unit and UI tests)
  - `requirements.in`, `requirements.txt` - dependency manifests
  - `app.py` - application entry point for local runs

## Development guidelines

- Follow the Flask application factory pattern already used in the project.
- Add new models in `academics/model/` and register migrations using Alembic.
- Keep controller (view) logic in `academics/` blueprints; keep business logic in `academics/services/`.
- Prefer small, focused commits with descriptive messages.
- Keep changes backwards-compatible where possible; if breaking changes are necessary, document them in the PR description.

Contract for changes (2–4 bullets):
- Inputs: HTTP request parameters / CLI args / config via `.env`.
- Outputs: HTTP responses, DB changes via SQLAlchemy, logs and optional file outputs.
- Error modes: Validate inputs and return appropriate 4xx responses; log unexpected errors and return 5xx.
- Success criteria: New or changed functionality covered by at least one test; no linting or syntax errors.

Edge cases to consider when editing code:
- Empty or missing inputs (None/empty string)
- Large result sets and pagination
- Uninitialized records (some models have an `initialised` flag)
- Authentication/authorization for UI and API endpoints
- Database migrations and compatibility across environments

## Testing

- Tests use `pytest`. Unit tests and UI tests live under `tests/` and follow the project's fixtures.
- Run all tests locally with:

```bash
pytest
```

- When adding features, write tests for happy path and at least one edge case (e.g., empty data, permission denied).
- Tests use fixtures from `tests/conftest.py` and helpers under `tests/` (faker objects are available for generating DB rows).

## Database / Migrations

- Models are SQLAlchemy-based in `academics/model/`.
- Use Alembic for schema changes. Example workflow:

```bash
# create a migration after changing models
flask db revision -m "describe change"
# apply locally
flask db upgrade
```

- Keep migrations small and documented; include a short rationale in migration message.

## Environment setup

1. Copy the example env and customize:

```bash
cp example.env .env
# edit .env to configure database URL and any other local settings
```

2. Install dependencies (project uses pip and pinned requirements):

```bash
pip install -r requirements.txt
```

3. Run migrations before starting the app if you need a DB schema:

```bash
flask db upgrade
```

4. Start the development server:

```bash
flask run
```

## Common tasks

- Adding a new route/view:
  - Add the view to the proper blueprint under `academics/`.
  - Add templates under `academics/ui/templates/` if needed.
  - Add tests under `tests/ui/views/`.

- Adding a new model:
  - Add the model to `academics/model/`.
  - Create an Alembic revision.
  - Update fixtures/tests as needed.

- Adding a background job:
  - Add job code under `academics/jobs/` or `scripts/`.
  - Wire it into the scheduler or celery worker if used.

## Admin / Security

- Authentication and authorization use patterns established in `academics/security.py`.
- Use decorators from `academics/decorators.py` for access control where applicable.

## Testing and CI notes

- Keep tests fast and deterministic. Use fixtures and database transaction rollbacks per test.
- If adding integration-heavy tests, consider marking them separately so they can be filtered in CI.

## Best practices

- Write clear docstrings for public functions and modules.
- Keep views thin; move business logic into services.
- Validate and sanitize user input at the boundary (forms/controllers).
- Use SQLAlchemy sessions consistently and close/rollback as needed in error cases.
- When touching critical or user-affecting flows, add both tests and a short changelog entry in the PR.

## Troubleshooting

- If migrations fail, ensure your DB URL in `.env` points to a local, writable DB and that no concurrent migration locks exist.
- If tests fail locally but pass in CI, check for environment differences (DB, env vars) and any test order dependencies.

## Where to look next

- App entry: `app.py`
- Models: `academics/model/`
- Blueprints/UI: `academics/` and `academics/ui/templates/`
- Tests & fixtures: `tests/` and `tests/conftest.py`

---

If you'd like, I can also:
- Add example PR checklist or template.
- Create a small README snippet containing the most common dev commands.
- Run the test suite after adding this file.

