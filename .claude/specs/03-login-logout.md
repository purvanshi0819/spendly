# Spec: Login and Logout

## Overview
This step implements authentication sessions for Spendly: `POST /login` verifies submitted credentials against the existing `users` table, starts a Flask session on success, and redirects into the app; `GET /logout` clears that session and returns the visitor to the public site. It is the first step that introduces server-side state (sessions) and depends on the user accounts created by Step 2's registration flow.

## Depends on
Step 1 — Database Setup (users table and `get_db` / `init_db` / `seed_db`).
Step 2 — Registration (accounts with Werkzeug-hashed passwords and `create_user`).

## Routes
- `POST /login` — validate credentials and start a session — public
- `GET /logout` — clear the active session — public (no-op when not logged in)

## Database changes
No schema changes. Login reuses the existing `users` table. Implementation adds a read-only helper `get_user_by_email(email)` to `database/db.py` so routes never embed SQL.

## Templates
- **Create:** None
- **Modify:** `templates/login.html` — change the form `action` to `{{ url_for('login') }}` (currently hardcoded to `/login`) so links follow the route name; keep the existing `error` block and POST method.
- **Modify:** `templates/base.html` — conditionally render auth links: when `session.user_id` is set, show a "Log out" link to `url_for('logout')`; otherwise show "Sign in" and "Get started" as today.

## Files to change
- `app.py` — convert `/login` to GET+POST, implement `/logout`, add session/secret-key and Werkzeug verification imports, wire `get_user_by_email`.
- `database/db.py` — add `get_user_by_email()`.
- `templates/login.html` — use `url_for()` for the form action.
- `templates/base.html` — session-aware navigation.

## Files to create
None.

## New dependencies
No new dependencies. `flask.session` and `werkzeug.security.check_password_hash` are already available through Flask and Werkzeug in `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords verified with Werkzeug `check_password_hash` (never compare plaintext)
- Passwords are never stored or logged in plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All internal links and form actions use `url_for()`
- Route functions keep one responsibility: fetch/validate data, render or redirect — no inline SQL
- Store the logged-in user's id in `session["user_id"]` (and optionally `session["user_name"]`)
- Set `app.secret_key` so sessions work in development; do not commit a production-grade secret
- Clear the entire session on logout via `session.clear()`
- Return generic "Invalid email or password." for any credential failure — do not reveal whether the email exists

## Definition of done
- [ ] Visiting `/login` renders the sign-in form without errors
- [ ] Submitting valid registered credentials starts a session (`session["user_id"]` is set) and redirects to `/profile`
- [ ] Submitting an unknown email or a wrong password re-renders `/login` with "Invalid email or password."
- [ ] Submitting missing email or password re-renders `/login` with an error message
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/`
- [ ] Visiting `/logout` while not logged in does not crash and redirects to `/`
- [ ] Login form action and nav links use `url_for`
- [ ] No SQL lives in `app.py`; credential lookup goes through `get_user_by_email`