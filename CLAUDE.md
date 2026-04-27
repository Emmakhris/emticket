# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Layout

Django project root is `emticket/` — all `manage.py` commands and app code live there.

```
TicketingApp/
└── emticket/           ← Django project root (cd here to run manage.py)
    ├── emticket/       ← project package (settings, urls, wsgi, celery)
    ├── accounts/
    ├── organizations/
    ├── tickets/
    ├── sla/
    ├── automations/
    ├── knowledgebase/
    ├── assets/
    ├── notifications/
    ├── audit/
    ├── reporting/
    └── templates/      ← global templates (base.html, registration/)
```

## Git & Version Control

Every meaningful change must be committed so the full history is navigable and any version is recoverable.

### Commit discipline

- Commit after each logical unit of work — a new feature, a bug fix, a migration, a config change. Do not batch unrelated changes into one commit.
- Commit messages must follow this format:

  ```
  <type>(<scope>): <short summary>

  <body — what changed and why, not how>
  ```

  **Types:** `feat`, `fix`, `refactor`, `style`, `test`, `chore`, `docs`, `migration`
  **Scope:** the app or area affected, e.g. `tickets`, `sla`, `automations`, `accounts`, `docker`

  Examples:
  ```
  feat(tickets): add watcher notification on status change
  fix(sla): shift resolution due date correctly after resume from on_hold
  migration(accounts): add role field to UserProfile
  chore(docker): pin postgres image to 16.3
  ```

- Always stage specific files — never `git add .` blindly. Exclude `.env`, `*.pyc`, `__pycache__/`, and `media/` (these should be in `.gitignore`).
- Each migration gets its own commit with a `migration(<app>):` prefix so it can be identified and reverted independently.

### Pushing to GitHub

```bash
# Check what will be committed before staging
git status
git diff

# Stage specific files
git add emticket/tickets/views.py emticket/tickets/models.py

# Commit
git commit -m "feat(tickets): add confidential ticket flag to create form"

# Push to GitHub
git push origin main

# If working on a feature, use a branch
git checkout -b feat/sla-breach-notifications
git push -u origin feat/sla-breach-notifications
```

### Reverting to a previous version

```bash
# View history to find the commit to revert to
git log --oneline

# Undo the last commit but keep changes staged
git reset --soft HEAD~1

# Revert a specific commit by hash (safe, creates a new commit)
git revert <commit-hash>

# Restore a single file to its state at a specific commit
git checkout <commit-hash> -- emticket/tickets/models.py
```

Use `git revert` over `git reset --hard` when the commit has already been pushed to GitHub.

## Common Commands

All commands must be run from `emticket/`.

```bash
# Start all services (web, worker, beat, db, redis)
docker compose up --build

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --no-input

# Run the dev server (requires a running Postgres + Redis)
python manage.py runserver

# Run all tests
python manage.py test

# Run tests for a single app
python manage.py test tickets
python manage.py test sla

# Run a single test case
python manage.py test tickets.tests.TicketCreateTests.test_create_ticket

# Start Celery worker manually
celery -A emticket worker -l INFO

# Start Celery beat scheduler manually
celery -A emticket beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Environment

Requires a `.env` file at `emticket/.env`. Required variables:

```
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=emticket
POSTGRES_USER=emticket
POSTGRES_PASSWORD=emticket
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## Architecture

### Service Layer Pattern

Business logic lives in `services.py` files inside each app — **never directly in views**:

- `sla/services.py` — `initialize_or_recompute_sla()`, `mark_first_response()`, `on_ticket_status_change()`, `resolve_sla_policy()`
- `automations/services.py` — `run_ticket_automations(ticket, trigger, actor, changes, extra)`

Views call these services; signals or Celery tasks also call them. This is the established pattern for new features.

### Ticket Lifecycle & SLA

1. **Creation** → `initialize_or_recompute_sla()` computes due dates via `WorkingCalendar` (business-hours-aware, per-site timezone).
2. **Status change** → `on_ticket_status_change()` handles pause/resume. SLA clocks pause on `on_hold` / `waiting_requester`; paused wall-clock time is tracked in `SLAStatus.total_paused_seconds` and shifted into the due dates on resume.
3. **First agent reply** → `mark_first_response()` sets `Ticket.first_response_at` and transitions NEW → OPEN.
4. **Background scan** → Celery beat runs `sla_scan_and_escalate()` every 60 s to detect breaches and fire escalation actions.

SLA policy resolution precedence (highest → lowest specificity): `category + site + priority` → `category + priority` → `department + priority`.

### Automation Engine

`run_ticket_automations()` is called after every ticket create/update/comment and on SLA breach. It:
1. Loads `AutomationRule` rows for the org + trigger.
2. Evaluates `conditions` (JSON AND/OR tree) via `automations/conditions.py`.
3. Dispatches `actions` via `automations/engine.py` (action registry pattern).

Pass `changes={"field": (old_val, new_val)}` when calling from an update so `changed` / `changed_to` / `changed_from` operators work correctly.

### Access Control

`_user_can_view_ticket(user, ticket)` in `tickets/views.py` is the single gate for ticket visibility. Confidential tickets restrict to requester/assignee/same-team. Expand this function as RBAC matures — there is no separate permission class yet.

### HTMX Partial Rendering

Views check `request.headers.get("HX-Request")` to return partial templates instead of full pages. Partials live at `tickets/templates/tickets/partials/` (table rows, sidebar, comment thread, attachments). Always return the matching partial from HTMX-triggered endpoints.

### Ticket Numbering

`TicketSequence` uses `SELECT FOR UPDATE` to generate collision-free `ticket_number` values scoped per org/department/year. Never generate ticket numbers outside this mechanism.

### Multi-tenancy

Everything is scoped to `Organization`. Queries on tickets, SLA policies, automation rules, and KB articles must always filter by `organization_id`. Do not assume a single-org deployment.

### Frontend Stack

Tailwind CSS (CDN), Alpine.js (CDN), HTMX (CDN) — no build step. Static assets served by WhiteNoise. No npm/webpack involved.
