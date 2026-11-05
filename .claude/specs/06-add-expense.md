# Spec: Add Expense

## Overview
This step replaces the `/expenses/add` stub with a working page that lets a logged-in user create a new expense. It introduces the first write flow for expense data: a form captures amount, category, date, and optional description, validates the input, inserts a new row into the `expenses` table linked to the current user, and redirects back to the profile page where the new entry appears. It builds on the database layer (Step 1), authentication (Steps 2–3), profile page (Step 4), and date filter (Step 5).

## Depends on
- Step 1 — Database Setup (`expenses` table, `get_db()`)
- Step 2 — Registration (user accounts)
- Step 3 — Login and Logout (session, protected routes)
- Step 4 — Profile Page (`profile()` view, `/profile` redirect target)
- Step 5 — Date Filter (profile renders filtered expenses)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only (redirects unauthenticated visitors to `/login`)
- `POST /expenses/add` — validate and insert the expense, then redirect to `/profile` — logged-in only

## Database changes
No schema changes. Add one write helper to `database/db.py`:
- `create_expense(user_id, amount, category, date_str, description=None)` — inserts a row into `expenses` with parameterised queries and returns the new row id.

## Templates
- **Create:** `templates/add_expense.html` — form extending `base.html` with fields for amount, category (select from the fixed list), date, and description, plus a submit button and a back/cancel link to `/profile`.
- **Modify:** none required (profile already links to `add_expense` via `url_for`).

## Files to change
- `app.py` — replace the `/expenses/add` stub with a view that accepts `GET` and `POST`, guards on `session["user_id"]`, validates form input, calls `create_expense`, and redirects to `profile` on success; renders the form with errors on invalid input. Import `create_expense`.
- `database/db.py` — add `create_expense()`.

## Files to create
- `templates/add_expense.html`
- `static/css/add_expense.css` — page-specific styling using CSS variables only.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All internal links and form actions use `url_for()`
- Route functions keep one responsibility: guard → validate → persist → redirect
- Auth guard: if `session.get("user_id")` is missing, redirect to `url_for("login")`; if the user row cannot be found, clear the session and redirect to login
- Valid categories are the fixed list from Step 1: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- Validate `amount` is present and non-negative (store as REAL); validate `date` is a valid ISO `YYYY-MM-DD`; `description` is optional and may be empty/None
- On validation failure, re-render the form with an `error` message and preserve submitted values; do not insert a partial row
- After successful insert, redirect to `url_for("profile")` (no raw 302 Location hardcoding in template)
- Use `abort()` for HTTP errors, not bare string returns

## Definition of done
- [ ] Visiting `/expenses/add` while not logged in redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in returns 200 and renders the form
- [ ] Submitting a valid expense redirects to `/profile` and the new entry appears in the list
- [ ] The new expense shows the submitted amount, category, date, and description on `/profile`
- [ ] Submitting with missing/invalid amount or date re-renders the form without inserting a row
- [ ] An invalid category is rejected
- [ ] `/profile` summary stats and category breakdown reflect the newly added expense
- [ ] All links and form actions use `url_for()`
- [ ] No SQL lives in `app.py`; inserts go through `create_expense`
- [ ] No hex colour values in `add_expense.html`