Test fix: call django.setup() in `scripts/run_test_task.py` to avoid AppRegistryNotReady

What I changed
- Added `django.setup()` at the start of `scripts/run_test_task.py` so the Django app registry is initialized before running Celery tasks synchronously (using `.apply()` in the test harness).

Why
- Running `remove_reservations_for_category_schedule.apply(...)` in the test script previously raised `django.core.exceptions.AppRegistryNotReady: Apps aren't loaded yet.`
- Calling `django.setup()` ensures models and the app registry are ready when tasks run synchronously in local tests.

How I tested it
- Ran the script under the project venv with `DJANGO_SETTINGS_MODULE=diners.settings.local_sqlite`:
  - `create_transaction_task.apply(...)` → returned the expected mock response
  - `remove_reservations_for_category_schedule.apply(...)` → returned `True` (no AppRegistry error)

Suggested next steps
- When Docker is available, run Redis + a Celery worker with the project's `docker-compose.yml` and validate the `.delay()` path end-to-end.
- Optionally add a CI check to run this script in eager mode as a lightweight integration test.

Please review and let me know if you'd like me to post this as a comment directly to the PR (I can do that if you provide GH CLI access or a GitHub API token), or if you'd prefer I open/format the comment in the PR description instead.
