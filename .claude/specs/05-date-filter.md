# Spec: Date Filter

## Overview
Add date-range filtering to the profile page so a logged-in user can view a subset of
their expenses by start and end date. The filter is submitted as a GET form and
surfaced through query parameters (`start_date`, `end_date`) on `/profile`, so filtered
views are shareable and bookmarkable. Quick preset chips (This month, Last 3 months,
All time) are also supported via an optional `range` query parameter (`this_month`,
`last_3_months`, `all_time`); a present `range` takes precedence over manual dates.
Summary stats (total spent, transaction count, top category) and the category
breakdown must reflect the filtered set, not the entire history. Filtering reuses the
existing ISO `YYYY-MM-DD` date column for safe, parameterized range comparison—no
schema or dependency changes.

## Depends on
- Step 1 — Database Setup: `expenses.date` TEXT ISO column, `get_db()` with row factory + FK enforcement.
- Step 4 — Profile Page: `profile()` view, `get_user_by_id`, `get_expenses_by_user`, `profile.html`.

## Routes
- `GET /profile` (existing, modified) — accepts optional `start_date`, `end_date`, and
  `range` (`this_month` | `last_3_months` | `all_time`) query params; auth-gated
  (logged-in). `range` takes precedence over manual dates. No new route.

## Database changes
No database changes. `get_expenses_by_user` gains optional `start_date` and `end_date`
parameters; conditions are added with parameterised `?` placeholders only.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — add GET preset chips (This month, Last 3 months,
  All time) plus a custom start/end date form with Apply button, a "Clear filter"
  control; preserve selected values/range; render filtered expense list and derived
  stats/breakdown for the filtered result set.

## Files to change
- `database/db.py` — modify `get_expenses_by_user`
- `app.py` — modify `profile()` to read/validate query params and pass filter state to template
- `templates/profile.html` — add filter form + state display
- `static/css/profile.css` — style filter form (CSS variables only)

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
- Auth guard on `/profile` preserved (redirect unauthenticated users to `/login`)
- Empty/invalid date inputs must not crash; treat as "no bound"

## Definition of done
- [ ] `GET /profile` while logged in returns 200 (no filter)
- [ ] `GET /profile?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` returns 200
- [ ] `GET /profile?range=this_month` (and `last_3_months`, `all_time`) returns 200
- [ ] Only expenses with date within the range are listed
- [ ] Stats and category breakdown reflect the filtered set
- [ ] Invalid/empty date params do not error; page still renders
- [ ] `Clear filter` resets to full list
- [ ] Unauthenticated requests redirect to `/login`
- [ ] No SQL in `app.py`; all bounds parameterised in `db.py`
- [ ] No hex colour values in `profile.html`
- [ ] All filter controls use `url_for()` / GET form (no hardcoded paths)
