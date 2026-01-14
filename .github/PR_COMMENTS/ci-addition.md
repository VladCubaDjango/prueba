Title: CI: Add GitHub Actions workflow to run flake8 and Django tests (local sqlite)

## Summary
Adds a GitHub Actions workflow and flake8 configuration to run project linters and tests on push and PRs.

## What changed
- `.github/workflows/ci.yml` — workflow that:
  - sets up Python (3.11, 3.12)
  - installs dependencies from `requirements.txt`
  - runs `python manage.py migrate --noinput` using `diners.settings.local_sqlite`
  - runs `flake8 .`
  - runs `python -m django test --settings=diners.settings.local_sqlite -v 2`
- `.flake8` — basic flake8 config (max line length 88, ignores E203/W503)

## Why
- Ensure tests and linting run for every PR and push to catch regressions early.
- Use the `local_sqlite` settings so CI runs offline (no external GraphQL or Redis required) and Celery tasks run in eager mode for deterministic tests.

## How to test locally
1. Ensure you have a Python venv with project deps: `pip install -r requirements.txt`.
2. Run migrates: `DJANGO_SETTINGS_MODULE=diners.settings.local_sqlite python manage.py migrate --noinput`.
3. Run flake8: `flake8 .`.
4. Run tests: `python -m django test --settings=diners.settings.local_sqlite -v 2`.

## Notes / Follow-ups
- I added a placeholder `integration` job that is `workflow_dispatch`-triggered for future E2E tests using docker-compose (Postgres + Redis + Celery worker). I can implement this job if you want me to configure the docker-compose steps and the integration tests.

## Request for review
Please review the workflow, `.flake8`, and confirm if you want a manual integration job implemented now (Postgres+Redis+Worker) or left for future work.

---

(Automated comment file created by Git operations in branch `add/indexes-reservation-menu`.)