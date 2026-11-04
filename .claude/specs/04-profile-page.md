# Spec: Profile Page

## Overview
This feature replaces the `/profile` stub with a fully designed profile page showing static, hardcoded data. The goal is to establish the complete UI layout — user info card, transaction history table, summary stats, and category breakdown — before any real database queries are wired up in Step 5. Building the UI first lets the team validate the design in isolation and ensures the templates are ready for the backend-connection step.

## Depends on
- Step 1: Database setup (schema must exist)
- Step 2: Registration (user accounts must be creatable)
- Step 3: Login + Logout (session must be set; `/profile` must be a protected route)

## Routes
- GET /profile — render the profile page — logged-in only (redirect to /login if not authenticated)

## Database changes
No database changes. The existing `users` and `expenses` tables are sufficient.

## Templates
- Create: `templates/profile.html` — full profile page extending `base.html`; contains four sections:
  1. **User info card** — avatar initials, name, email, member-since date (all hardcoded)
  2. **Summary stats row** — total spent, number of transactions, top category (hardcoded)
  3. **Transaction history table** — list of recent expenses with date, description, category badge, amount (hardcoded rows)
  4. **Category breakdown** — per-category totals displayed as a simple list or progress-bar rows (hardcoded)

## Files to change
- `app.py` — replace the `/profile` stub with a real view function that:
  - Redirects unauthenticated users to `/login`
  - Passes hardcoded context variables to `profile.html`

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw sqlite3 via `get_db()` if any DB call is ever needed
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Authentication guard: check `session.get("user_id")`; if absent, `redirect(url_for("login"))`
- All data passed to the template must be hardcoded Python dicts/lists in `app.py` — no DB queries in this step
- Category badges must use a CSS class, not inline colour styles

## Definition of done
- [ ] Visiting `/profile` without being logged in redirects to `/login`
- [ ] Visiting `/profile` while logged in returns HTTP 200
- [ ] The page displays a user info card with a name and email
- [ ] The page displays at least three summary stat values (e.g. total spent, transaction count, top category)
- [ ] The page displays a transaction history table with at least three hardcoded rows
- [ ] The page displays a category breakdown section with at least three categories
- [ ] The navbar shows the logged-in state (username + logout link)
- [ ] No hex colour values appear in `profile.html` — only CSS variables

<!-- # Spec: Profile Page

## Overview
This step turns the `/profile` stub into a real, authenticated page that shows the logged-in user's account details and their personal list of expenses. It is the first feature that reads and displays user-specific data from the database, bridging authentication (Steps 2–3) with the upcoming expense-management steps (7–9). The page must be the landing destination after login and registration, and it must gracefully redirect unauthenticated visitors to login.

## Depends on
- Step 1 — Database Setup (`users` and `expenses` tables, `get_db` / `init_db` / `seed_db`).
- Step 2 — Registration (`create_user`, hashed passwords).
- Step 3 — Login and Logout (`session["user_id"]` / `session["user_name"]`, `/logout`).

## Routes
- `GET /profile` — render the authenticated user's profile and expenses — logged-in only (redirects unauthenticated visitors to `url_for("login")`).

## Database changes
No schema changes. Add two read-only helpers to `database/db.py`:
- `get_user_by_id(user_id)` — return the user row (or `None`) for the given id.
- `get_expenses_by_user(user_id)` — return the rows in `expenses` belonging to that user (ordered by date descending, then id descending).

All SQL stays in `database/db.py`; routes never embed SQL. Parameterised queries only.

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; shows the user's name, an "Add expense" link, and an expenses table (date, category, description, amount) with per-row edit/delete links. Empty state when there are no expenses. Links must use `url_for()` (`add_expense`, `edit_expense`, `delete_expense`, `logout`).
- **Modify:** `templates/base.html` — no change required (already session-aware). Page-specific styles live in a new CSS file included via `{% block head %}`.

## Files to change
- `app.py` — implement `profile()` route: guard on `session["user_id"]`, load user + expenses via helpers, render `profile.html`. Import the new helpers from `database.db`.
- `database/db.py` — add `get_user_by_id()` and `get_expenses_by_user()`.

## Files to create
- `templates/profile.html`
- `static/css/profile.css` — page-specific styling using CSS variables only.

## New dependencies
No new dependencies. Everything required (`flask.session`, Jinja2) is already available.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with Werkzeug (no password display/edit on this page)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All internal links and form actions use `url_for()`
- Route functions keep one responsibility: guard → fetch → render; no inline SQL
- Auth guard: if `session.get("user_id")` is missing, redirect to `url_for("login")`; if the user row cannot be found, clear the session and redirect to login (do not crash)
- Keep `amount` rendered raw (do not force 2-decimal formatting) so values like `12.5` appear verbatim; prefix with the rupee symbol `₹` without altering the number
- Do not implement `/expenses/add`, `/expenses/<id>/edit`, or `/expenses/<id>/delete` here — only link to them via `url_for()`
- Expenses with a `NULL` description must render without error (fall back to an empty/placeholder display)

## Definition of done
- [ ] Visiting `/profile` while logged in returns 200 and renders without errors
- [ ] The page contains the logged-in user's name (e.g. `Alice`)
- [ ] The page lists the logged-in user's expenses, including the description (e.g. `lunch`) and amount (e.g. `12.5`) as substrings
- [ ] After editing an expense (Step 8 flow), the profile reflects the updated description (e.g. `dinner`)
- [ ] After deleting an expense (Step 9 flow), the profile no longer shows that item
- [ ] Visiting `/profile` while not logged in redirects to `/login` (no crash)
- [ ] Visiting `/profile` after `session.clear()` redirects to `/login`
- [ ] All links on the page (add/edit/delete/logout) use `url_for()` (no hardcoded paths)
- [ ] No SQL lives in `app.py`; lookups go through `get_user_by_id` / `get_expenses_by_user`
- [ ] Empty expense list renders an empty-state message without error -->