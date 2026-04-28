# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Layout

Django project root is `emticket/` — all `manage.py` commands and app code live there.

```
TicketingApp/
├── venv/               ← Python virtualenv (activate before running manage.py locally)
└── emticket/           ← Django project root (cd here to run manage.py)
    ├── emticket/       ← project package (settings, urls, wsgi, celery)
    ├── accounts/       ← users, roles, UserProfile, RBAC, RequesterPortalMiddleware
    ├── organizations/  ← Organization, Site, Department, Team, WorkingCalendar
    ├── tickets/        ← core: Ticket, TicketComment, TicketAttachment, CSAT, CannedResponse
    ├── sla/            ← SLAPolicy, SLAStatus, Celery beat scan task
    ├── automations/    ← AutomationRule, condition evaluator, action dispatcher
    ├── knowledgebase/  ← KBArticle, KBCategory, KBArticleFeedback
    ├── assets/         ← Asset, AssetType, AssetLocation (CMDB)
    ├── notifications/  ← Notification, email.py, Celery email task
    ├── audit/          ← AuditEvent, log_event() service
    ├── reporting/      ← dashboard stats, analytics, SavedView
    ├── portal/         ← requester-facing portal (my tickets, CSAT)
    └── templates/      ← global templates; app templates live here too (not in app dirs)
```

All templates are in `emticket/templates/<app>/` — **not** inside app directories. `APP_DIRS=True` is set but the global `DIRS` takes precedence.

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

- Always stage specific files — never `git add .` blindly.
- Each migration gets its own commit with a `migration(<app>):` prefix.

### Pushing to GitHub

Remote: `https://github.com/Emmakhris/emticket.git`

```bash
git push origin main
```

Use `git revert` over `git reset --hard` when the commit has already been pushed.

## Common Commands

All commands must be run from `emticket/`. Activate the venv first for local dev:

```bash
# Activate venv (Windows)
source ../venv/Scripts/activate

# Start all services (web, worker, beat, db, redis) — requires Docker Desktop running
docker compose up --build

# Run migrations
python manage.py migrate

# Create superuser (required before first login)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --no-input

# Run the dev server (requires Postgres + Redis running separately)
python manage.py runserver

# Run all tests
python manage.py test

# Run tests for a single app
python manage.py test tickets

# Start Celery worker manually
celery -A emticket worker -l INFO

# Start Celery beat scheduler manually
celery -A emticket beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Environment

Requires a `.env` file at `emticket/.env`. Required variables:

```
DJANGO_SECRET_KEY=<long random string>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=emticket
POSTGRES_USER=emticket
POSTGRES_PASSWORD=emticket
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=no-reply@hospital.org
```

For production: set `DJANGO_DEBUG=False`, configure real SMTP, use a 50+ char secret key. `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are already tied to `not DEBUG` in settings.

## URL Structure

| Prefix | App | Notes |
|---|---|---|
| `/` | `reporting` | Dashboard at root |
| `/tickets/` | `tickets` | List, create, detail, bulk actions, CSV export |
| `/users/` | `accounts` | User management (admin/supervisor only) |
| `/organizations/` | `organizations` | Org/site/dept/team/calendar management |
| `/assets/` | `assets` | CMDB — asset list, detail, create/edit |
| `/automations/` | `automations` | Rule builder UI |
| `/sla/` | `sla` | SLA policy matrix |
| `/notifications/` | `notifications` | Bell count, list, mark-read |
| `/kb/` | `knowledgebase` | Articles, edit, feedback, suggest |
| `/portal/` | `portal` | Requester portal (auto-redirect for requester role) |
| `/accounts/` | `django.contrib.auth` | Login, logout, password reset |
| `/admin/` | Django admin | Fallback management |

## Architecture

### Service Layer Pattern

Business logic lives in `services.py` — **never directly in views**:

- `sla/services.py` — `initialize_or_recompute_sla()`, `mark_first_response()`, `on_ticket_status_change()`, `resolve_sla_policy()`
- `automations/services.py` — `run_ticket_automations(ticket, trigger, actor, changes, extra)`
- `audit/services.py` — `log_event(*, organization, actor, event_type, object_type, object_id, before, after, metadata, request)`
- `reporting/services.py` — `get_dashboard_stats()`, `get_volume_by_day()`, `get_sla_compliance()`, `get_agent_workload()`, `get_category_breakdown()`
- `knowledgebase/services.py` — `get_suggested_articles(ticket)`, `get_suggested_articles_by_query(org, query)`
- `tickets/services.py` — `calculate_priority(impact, urgency)` (ITIL impact×urgency matrix)

### Ticket Lifecycle & SLA

1. **Creation** → `initialize_or_recompute_sla()` computes due dates via `WorkingCalendar` (business-hours-aware, per-site timezone). Priority is auto-calculated from `impact × urgency` — never set it directly from the form.
2. **Status change** → `on_ticket_status_change()` handles pause/resume. SLA clocks pause on `on_hold` / `waiting_requester`.
3. **First agent reply** → `mark_first_response()` sets `Ticket.first_response_at` and transitions NEW → OPEN.
4. **Background scan** → Celery beat runs `sla_scan_and_escalate()` every 60 s via `emticket/celery.py` beat schedule.

SLA policy resolution precedence: `category + site + priority` → `category + priority` → `department + priority`.

### Automation Engine

`run_ticket_automations()` is called after every ticket create/update/comment and on SLA breach. The engine:
1. Loads `AutomationRule` rows for the org + trigger.
2. Evaluates `conditions` (JSON AND/OR tree) via `automations/conditions.py`.
3. Dispatches `actions` via `automations/engine.py` (action registry).
4. Respects `rule.run_once` (default `True`) — skips rules already run on this ticket.
5. Supports `dry_run=True` for the "Test Rule" button.

Pass `changes={"field": (old_val, new_val)}` when calling from an update so `changed_to` / `changed_from` operators work.

### Access Control

- `accounts/permissions.py` — `require_role(*roles)` decorator, `can_view_ticket(user, ticket)`
- `accounts/middleware.py` — `RequesterPortalMiddleware` auto-redirects users with `role=="requester"` to `/portal/`
- Roles: `admin`, `supervisor`, `team_lead`, `agent`, `requester`
- Ticket visibility gate: `can_view_ticket()` imported as `_user_can_view_ticket` in `tickets/views.py`

### HTMX Partial Rendering

Views check `request.headers.get("HX-Request") == "true"` to return partials. Key partials:

| Partial | Trigger |
|---|---|
| `tickets/partials/table.html` | Filter form, pagination |
| `tickets/partials/sidebar.html` | Status change, assign, unassign |
| `tickets/partials/thread.html` | Add comment, add attachment |
| `notifications/partials/bell_count.html` | Every 30s poll + mark-read |
| `reporting/partials/saved_views.html` | Save/delete filter |

**Important:** The sidebar partial needs `ticket`, `status_choices`, and `assignee_options`. Always use `_sidebar_ctx(ticket, request)` from `tickets/views.py` when rendering it — never build the context inline.

### Notification & Email Flow

1. Create a `Notification` object.
2. Call `send_notification_email.delay(notification.pk, event_type)` — the Celery task in `notifications/tasks.py` maps event types to template prefixes.
3. Templates in `templates/notifications/email/` follow the pattern `<prefix>.txt`, `<prefix>.html`, `<prefix>_subject.txt`.

Event types: `ticket.created`, `ticket.commented`, `ticket.assigned`, `sla.first_response_breached`, `sla.resolution_breached`.

### Ticket Numbering

`TicketSequence` uses `SELECT FOR UPDATE` to generate collision-free `ticket_number` values scoped per org/department/year. Never generate ticket numbers outside this mechanism.

### Multi-tenancy

Everything is scoped to `Organization`. Always filter by `organization_id`. The org comes from `request.user.profile.organization`. Do not assume single-org deployment.

### Frontend Stack

Tailwind CSS (CDN), Alpine.js (CDN), HTMX (CDN) — no build step. No npm/webpack. Static assets served by WhiteNoise. CSRF token for HTMX is injected globally via `htmx:configRequest` listener in `base.html`.

### KB Article Rendering

`knowledgebase/views.py` renders article bodies with `markdown` → `bleach` (HTML sanitization). Both packages are in `requirements.txt`. Always use `_render_body(raw)` — never render markdown directly to template.

## Key Patterns to Follow

**Adding a new HTMX-powered list page:**
- View checks `HX-Request` → returns table partial; otherwise full page
- Filter form uses `hx-get`, `hx-target="#tableDiv"`, `hx-push-url="true"`
- Paginator(qs, 50) always

**Adding a new audit-logged action:**
```python
from audit.services import log_event
log_event(organization=ticket.organization, actor=request.user,
          event_type="ticket.xxx", object_type="Ticket",
          object_id=ticket.id, before={...}, after={...}, request=request)
```

**Adding a new notification:**
```python
from notifications.models import Notification
from notifications.tasks import send_notification_email
notif = Notification.objects.create(organization=..., user=..., ticket=..., title=..., body=...)
send_notification_email.delay(notif.pk, "ticket.event_type")
```

**Adding a new automation trigger:** add the trigger string to `run_ticket_automations()` calls, add a matching condition/action handler in `automations/conditions.py` and `automations/actions.py`.

## Template Naming Conventions

- Full pages: `<app>/<noun>.html` (e.g. `tickets/detail.html`, not `details.html`)
- List pages: `<app>/<noun>_list.html`
- Form pages: `<app>/<noun>_form.html`  
- HTMX partials: `<app>/partials/<noun>_<fragment>.html`

**Known past mistake:** the ticket detail template was accidentally named `details.html` (with an 's') instead of `detail.html`. The view references `tickets/detail.html` — match it exactly.

## Docker

The `Dockerfile` and `docker-compose.yml` live in `emticket/` (the Django project root). The build context is `emticket/`. Five services: `db` (Postgres 16), `redis` (Redis 7), `web` (gunicorn), `worker` (Celery worker), `beat` (Celery beat with DatabaseScheduler).

Requires Docker Desktop to be running before `docker compose up --build`.
