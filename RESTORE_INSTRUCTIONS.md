Restoring production environment and switching between local dev and production

Overview
- This project includes a `diners.settings.local_sqlite` settings file intended for fast local development and offline testing. It uses an in-memory SQLite DB for tests, a `MockGraphqlService`, and `CELERY_TASK_ALWAYS_EAGER = True` so tasks run synchronously.

Reverting to production
1. Set the Django settings module to production or development as appropriate:
   - Production (example): `export DJANGO_SETTINGS_MODULE=diners.settings.production`
   - Development (example): `export DJANGO_SETTINGS_MODULE=diners.settings.development`
2. Ensure environment variables and secrets are set (database URL, GraphQL endpoint, API credentials, Redis URL, etc.). Check `diners/settings/production.py` and your environment for required vars.
3. Install production dependencies from `requirements.txt` (ensure you have any packages removed for the local dev shim re-added if necessary).
4. Run database migrations against the production DB: `python -m django migrate --settings=diners.settings.production`.
5. Start services (if using Docker): `docker-compose up -d` (Postgres, Redis, Celery worker). Confirm Celery worker is connected to the broker.
6. Run any management commands needed for production data sync.

Testing GraphQL and Celery in production-like environment
- The local tests use `diners.utils.mock_graphql.MockGraphqlService`. To test against the real GraphQL service, ensure your environment points to the real endpoint and valid credentials, then run the integration tests or manual smoke tests that exercise `GRAPHQL_SERVICE` calls.
- For Celery `.delay()` path tests, start `redis` and a `celery` worker via `docker-compose` and run a sample task that uses `.delay()`; verify the worker processes it.

Notes and safety
- The `mock_graphql` module is only used by `diners.settings.local_sqlite` and does not change production behavior.
- We added test coverage and non-destructive optimizations (cached GraphQL calls during a single request, reduced DB queries in admin bulk operations).
- Before deploying changes to production, ensure all tests (unit + integration + E2E) pass and review any changes that alter deletion semantics (bulk deletes bypass Django signals).

If you'd like, I can prepare a small checklist or CI job that runs a smoke E2E with docker-compose when Docker is available.