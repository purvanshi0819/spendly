# Spec: Registration

## Overview
This step implements user registration for Spendly: the `GET /register` form (already rendered) is paired with a `POST /register` handler that validates the submitted name, email, and password, hashes the password with Werkzeug, and persists a new row in the existing `users` table. It is the first authentication-related feature and depends on the database layer from Step 1; login and profile functionality in later steps will build on the accounts created here.

## Depends on
Step 1 — Database Setup (users table and db helpers must exist).

## Routes
- `POST /register` — validate and create a new user account — public

## Database changes
No database schema changes. Registration reuses the existing `users` table created in Step 1. Implementation adds a `create_user(name, email, password_hash)` helper to `database/db.py` to keep SQL out of route handlers.

## Templates
- **Create:** None
- **Modify:** `templates/register.html` — change form `action` to use `url_for('register')` (currently hardcoded to `/register`), preserving the existing `error` block.

## Files to change
- `app.py` — add `POST` handling to the `register` route (method validation, input validation, hashing, DB insert, redirect on success, error rendering on failure).
- `database/db.py` — add `create_user()` helper.
- `templates/register.html` — use `url_for()` for the form action.

## Files to create
None.

## New dependencies
No new dependencies. Werkzeug is already available via `requirements.txt`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Route functions keep one responsibility: fetch/validate data, render or redirect — no inline SQL
- Validate name, email, and password presence server-side; require password length >= 8
- Detect duplicate emails and surface a friendly error instead of crashing
- Never store plaintext passwords
- Redirect to `url_for('login')` on successful registration

## Definition of done
- [ ] Visiting `/register` renders the registration form without errors
- [ ] Submitting a complete, unique registration stores a new user with a Werkzeug-hashed password (no plaintext) and redirects to `/login`
- [ ] Submitting an email that already exists re-renders `/register` with an error message and creates no duplicate row
- [ ] Submitting missing fields or a password shorter than 8 characters re-renders `/register` with an error message
- [ ] Submitting mismatched password and confirm password re-renders `/register` with an error message
- [ ] Form action and all internal links use `url_for`
- [ ] All SQL remains parameterised and lives in `database/db.py`