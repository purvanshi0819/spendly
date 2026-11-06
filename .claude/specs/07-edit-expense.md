# Spec: Edit Expense

## Overview
This step replaces the `/expenses/<id>/edit` stub with a working page that lets a logged-in user edit an existing expense. It reuses the validation rules from the Add Expense step: a form is pre-filled with the expense's current values, accepts updates to amount, category, date, and description, validates input, persists the change through a new `update_expense` helper, and redirects back to the profile page where the updated entry appears. It builds on the database layer (Step 1), authentication (Steps 2–3), profile page and date filter (Steps 4–5), and Add Expense (Step 6).

## Depends on
- Step 1 — Database Setup (`expenses` table, `get_db()`)
- Step 2 — Registration (user accounts)
- Step 3 — Login and Logout (session, protected routes)
- Step 4 — Profile Page (`profile()` view, `/profile` redirect target)
- Step 5 — Date Filter (profile renders expenses)
- Step 6 — Add Expense (`create_expense`, validation rules, `add_expense.html` form pattern)

## Routes
- `GET /expenses/<int:id>/edit` — render a pre-filled edit form for an existing expense — logged-in only (redirects unauthenticated visitors to `/login`); returns 404 if the expense does not exist or does not belong to the current user
- `POST /expenses/<int:id>/edit` — validate and update the expense, then redirect to `/profile` — logged-in only; returns 404 if the expense does not exist or does not belong to the current user

## Database changes
No schema changes. Add two helpers to `database/db.py`:
- `get_expense_by_id(expense_id)` — return the expense row matching `id`, or `None`.
- `update_expense(expense_id, amount, category, date_str, description=None)` — update the matching row's amount, category, date, and description using parameterised queries.

Ownership is verified in the route (expense's `user_id` must equal `session["user_id"]`); the `expenses` table itself is unchanged.

## Templates
- **Create:** `templates/edit_expense.html` — form extending `base.html`, pre-filled from the loaded expense, with fields for amount, category (select from the fixed list), date, and description, plus a submit button and a cancel/back link to `/profile`.
- **Modify:** none required (profile already links to `edit_expense` via `url_for`).

## Files to change
- `app.py` — replace the `/expenses/<int:id>/edit` stub with a view accepting `GET` and `POST`: guard on `session["user_id"]`, load and ownership-check the expense, validate form input (same rules as Add Expense), call `update_expense`, redirect to `profile` on success; render the form with errors on invalid input. Import `get_expense_by_id` and `update_expense`.
- `database/db.py` — add `get_expense_by_id()` and `update_expense()`.

## Files to create
- `templates/edit_expense.html`
- `static/css/edit_expense.css` — page-specific styling using CSS variables only.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All internal links and form actions use `url_for()`
- Auth guard: if `session.get("user_id")` is missing, redirect to `url_for("login")`; if the user row cannot be found, clear the session and redirect to login
- Ownership: if the expense does not exist or its `user_id` differs from the current user, call `abort(404)`; never allow cross-user edits
- Validation mirrors Add Expense: amount present, non-negative, finite; category in the fixed list; date a valid ISO `YYYY-MM-DD`; description optional (empty/None allowed); enforce the same length limits (amount ≤ 20 chars, category ≤ 30 chars, description ≤ 500 chars)
- On validation failure, re-render the form with an `error` message, preserve submitted values, and do not persist a partial update
- On success, redirect to `url_for("profile")`
- Use `abort()` for HTTP errors, not bare string returns
- Pre-fill the form with the expense's stored values on GET (amount, category, date, description)

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while not logged in redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for a non-existent or foreign expense returns 404
- [ ] Visiting `/expenses/<id>/edit` while logged in returns 200 and renders a pre-filled form
- [ ] Submitting a valid update redirects to `/profile`
- [ ] The updated values (amount, category, date, description) appear on `/profile` and in the database
- [ ] Submitting with missing/invalid amount, category, or date re-renders the form without persisting a partial update
- [ ] An invalid category is rejected
- [ ] After editing, the profile summary stats and category breakdown reflect the new values
- [ ] All links and form actions use `url_for()`
- [ ] No SQL lives in `app.py`; lookups/updates go through `get_expense_by_id` / `update_expense`
- [ ] No hex colour values in `edit_expense.html`