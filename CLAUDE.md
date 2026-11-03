<!-- # CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

"Spendly" is a personal expense-tracking web app built with Flask, Jinja2 templates, and SQLite. It is organized as a step-by-step teaching project: `app.py` contains several placeholder routes (marked "coming in Step N") that students implement incrementally. Most backend pieces are stubs waiting to be filled in.

## Commands

Dependencies are in `requirements.txt` (Flask 3.1, Werkzeug 3.1, pytest 8.3, pytest-flask 1.3):

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Git Bash on Windows:
source venv/Scripts/activate
pip install -r requirements.txt
```

Run the dev server (port 5001, debug on):

```bash
python app.py
```

Run the test suite (none ships yet, but pytest/pytest-flask are available):

```bash
pytest
# single test:
pytest path/to/test_file.py::test_name
# by keyword:
pytest -k "substring"
```

The SQLite database file is `expense_tracker.db` at the repo root (gitignored). It is created/populated by the `database` package, which students implement.

## Architecture

- `app.py` — single Flask application. All routes are defined here. Public pages: `/` (landing), `/register`, `/login`, `/terms`, `/privacy`. Placeholder routes returning "coming soon" strings are intentionally unimplemented and correspond to later steps: `/logout`, `/profile`, `/expenses/add`, `/expenses/<int:id>/edit`, `/expenses/<int:id>/delete`.
- `database/` — `db.py` must provide three functions per its stub:
  - `get_db()` — returns a `sqlite3` connection with `row_factory` set and `PRAGMA foreign_keys = ON`.
  - `init_db()` — creates all tables with `CREATE TABLE IF NOT EXISTS`.
  - `seed_db()` — inserts sample development data.
  - `database/__init__.py` is empty.
- `templates/` — Jinja2 templates. `base.html` is the layout (navbar, footer, global CSS `static/css/style.css`, `static/js/main.js`). Pages extend it; `landing.html` additionally loads `static/css/landing.css`. Form templates (register/login) POST to `/register` and `/login` respectively and render an `error` variable when present.
- `static/` — `css/style.css` (global), `css/landing.css` (landing only), `js/main.js` (currently empty stub).
- DB path and auth handling are not yet wired; new routes should follow the existing url_for-based navigation and extend `base.html`. -->

# CLAUDE.md

## Project overview

Spendly is a lightweight personal expense tracker built with Flask and SQLite.

---

## Architecture
```
spendly/
├── app.py              # All routes — single file, no blueprints
├── database/
│   └── db.py           # SQLite helpers: get_db(), init_db(), seed_db()
├── templates/
│   ├── base.html       # Shared layout — all templates must extend this
│   └── *.html          # One template per page
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles
│   │   └── landing.css     # Landing-page-only styles
│   └── js/
│       └── main.js         # Vanilla JS only
└── requirements.txt
```

**Where things belong:**
- New routes → `app.py` only, no blueprints
- DB logic → `database/db.py` only, never inline in routes
- New pages → new `.html` file extending `base.html`
- Page-specific styles → new `.css` file, not inline `<style>` tags

---

## Code style

- Python: PEP 8, snake_case for all variables and functions
- Templates: Jinja2 with `url_for()` for every internal link — never hardcode URLs
- Route functions: one responsibility only — fetch data, render template, done
- DB queries: always use parameterized queries (`?` placeholders) — never f-strings in SQL
- Error handling: use `abort()` for HTTP errors, not bare `return "error string"`

---

## Tech constraints

- **Flask only** — no FastAPI, no Django, no other web frameworks
- **SQLite only** — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Vanilla JS only** — no React, no jQuery, no npm packages
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise
- Python 3.10+ assumed — f-strings and `match` statements are fine

---

## Subagent Policy
- Always use a builtin explore subagent for codebase exploration 
  before implementing any new feature
- Always use a subagent to verify test results 
  after any implementation
- When asked to plan, delegate codebase research 
  to a subagent before presenting the plan
- always use a builtin plan subagent in plan mode

---

## Commands
```bash
# Setup
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run a specific test file
pytest tests/test_foo.py

# Run a specific test by name
pytest -k "test_name"

# Run tests with output visible
pytest -s
```

---

## Implemented vs stub routes

| Route | Status |
|---|---|
| `GET /` | Implemented — renders `landing.html` |
| `GET /register` | Implemented — renders `register.html` |
| `GET /login` | Implemented — renders `login.html` |
| `GET /logout` | Stub — Step 3 |
| `GET /profile` | Stub — Step 4 |
| `GET /expenses/add` | Stub — Step 7 |
| `GET /expenses/<id>/edit` | Stub — Step 8 |
| `GET /expenses/<id>/delete` | Stub — Step 9 |

**Do not implement a stub route unless the active task explicitly targets that step.**

---

## Warnings and things to avoid

- **Never use raw string returns for stub routes** once a step is implemented — always render a template
- **Never hardcode URLs** in templates — always use `url_for()`
- **Never put DB logic in route functions** — it belongs in `database/db.py`
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync
- **Never use JS frameworks** — the frontend is intentionally vanilla
- **`database/db.py` is currently empty** — do not assume helpers exist until the step that implements them
- **FK enforcement is manual** — SQLite foreign keys are off by default; `get_db()` must run `PRAGMA foreign_keys = ON` on every connection
- The app runs on **port 5001**, not the Flask default 5000 — don't change this