# Spec: Delete Expense

## Overview
This step replaces the `/expenses/<int:id>/delete` stub with a working flow that lets a logged-in user remove one of their own expenses. It reuses the existing add/edit patterns for authentication and ownership checks: the expense is looked up, verified to belong to the current user, deleted through a new parameterised helper, and the user is redirected back to the profile page so the removed entry (and the derived summary stats and category breakdown) no longer appear. It builds on the database layer (Step 1), authentication (Steps 2–3), profile page and date filter (Steps 4–5), Add Expense (Step 6), and Edit Expense (Step 7).

## Depends on
- Step 1 — Database Setup (`expenses` table, `get_db()`)
- Step 2 — Registration (user accounts)
- Step 3 — Login and Logout (session, protected routes)
- Step 4 — Profile Page (`profile()` view, `/profile` redirect target)
- Step 5 — Date Filter (profile renders expenses)
- Step 6 — Add Expense (`create_expense`, form/validation patterns)
- Step 7 — Edit Expense (`get_expense_by_id`, ownership-check pattern)

## Routes
- `GET /expenses/<int:id>/delete` — delete an existing expense owned by the current user, then redirect to `/profile` — logged-in only (redirects unauthenticated visitors to `/login`); returns 404 if the expense does not exist or does not belong to the current user

## Database changes
No schema changes. Add one helper to `database/db.py`:
- `delete_expense(expense_id, user_id=None)` — delete the matching row using a parameterised query and return the affected row count. When `user_id` is provided, scope the delete to that owner so a mismatched id can never be touched by accident (defense in depth on top of the route-level ownership check).

The `expenses` table itself is unchanged.

## Templates
- **Create:** none (no dedicated page; deletion happens directly from the profile list)
- **Modify:** none required (profile already links to `delete_expense` via `url_for`)

## Files to change
- `app.py` — replace the `/expenses/<int:id>/delete` stub with a view that guards on `session["user_id"]`, loads and ownership-checks the expense, calls `delete_expense`, and redirects to `profile`; import `delete_expense`.
- `database/db.py` — add `delete_expense()`.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All internal links use `url_for()`
- Auth guard: if `session.get("user_id")` is missing, redirect to `url_for("login")`; if the user row cannot be found, clear the session and redirect to login
- Ownership: if the expense does not exist or its `user_id` differs from the current user, call `abort(404)`; never allow cross-user deletion
- No SQL lives in `app.py`; deletion goes through `delete_expense`
- Use `abort()` for HTTP errors, not bare string returns
- After successful deletion, redirect to `url_for("profile")`

## Definition of done
- [ ] Visiting `/expenses/<id>/delete` while not logged in redirects to `/login`
- [ ] Visiting `/expenses/<id>/delete` for a non-existent or foreign expense returns 404
- [ ] Visiting `/expenses/<id>/delete` while logged in deletes the expense and redirects to `/profile`
- [ ] The deleted entry no longer appears in `/profile` or in the database
- [ ] `/profile` summary stats and category breakdown reflect the deletion
- [ ] All links use `url_for()`
- [ ] No SQL lives in `app.py`; deletion goes through `delete_expense`
- [ ] No hex colour values are introduced