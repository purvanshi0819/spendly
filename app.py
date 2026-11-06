import sqlite3

import math
import re
from datetime import date, timedelta

CATEGORIES = ["Food", "Transport", "Bills", "Health",
              "Entertainment", "Shopping", "Other"]

from flask import Flask, render_template, request, redirect, url_for, session, abort

from database.db import (
    get_db, init_db, seed_db, create_user, get_user_by_email,
    get_user_by_id, get_expenses_by_user, create_expense,
    get_expense_by_id, update_expense, delete_expense,
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "spendly-dev-secret-key"


def _validate_expense_form(form, categories):
    """Validate an add/edit expense form.

    Returns (error, amount, category, expense_date, description, form_data).
    On failure ``error`` is a message and ``amount``/``expense_date`` are None.
    """
    amount_raw = (form.get("amount") or "").strip()
    category = (form.get("category") or "").strip()
    date_raw = (form.get("date") or "").strip()
    description_raw = (form.get("description") or "").strip()

    error = None
    amount = None
    expense_date = None

    if not amount_raw:
        error = "Amount is required."
    elif len(amount_raw) > 20:
        error = "Amount is too long."
    elif not re.fullmatch(r"^(\d+(\.\d*)?|\.\d+)$", amount_raw):
        error = "Amount must be a non-negative number."
    else:
        amount = float(amount_raw)
        if not math.isfinite(amount):
            error = "Amount must be a finite number."
        elif amount < 0:
            error = "Amount cannot be negative."

    if error is None and (not category or len(category) > 30 or category not in categories):
        error = "Please choose a valid category."

    if error is None and (not date_raw or len(date_raw) != 10 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_raw)):
        error = "Please enter a valid date."
    if error is None:
        try:
            expense_date = date.fromisoformat(date_raw).isoformat()
        except (ValueError, TypeError):
            expense_date = None
            error = "Please enter a valid date."

    if error is None and len(description_raw) > 500:
        error = "Description is too long."

    description = description_raw or None if error is None else None
    form_data = {
        "amount": amount_raw,
        "category": category,
        "date": date_raw,
        "description": description_raw,
    }
    return error, amount, category, expense_date, description, form_data

# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""
    confirm_password = request.form.get("confirm_password") or ""

    if not name:
        return render_template("register.html", error="Name is required.")
    if not email or "@" not in email:
        return render_template("register.html", error="Email is required.")
    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")
    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    password_hash = generate_password_hash(password)

    try:
        create_user(name, email, password_hash)
    except sqlite3.IntegrityError:
        return render_template("register.html", error="An account with that email already exists.")

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = (request.form.get("email") or "").strip()
    password = request.form.get("password") or ""

    if not email:
        return render_template("login.html", error="Email is required.")
    if not password:
        return render_template("login.html", error="Password is required.")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # Parse optional date filters from query string (never trust raw input).
    def _parse_iso(value):
        value = (value or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            return None

    allowed_ranges = {"this_month", "last_3_months", "last_6_months", "all_time"}
    selected_range = (request.args.get("range") or "").strip()
    if selected_range not in allowed_ranges:
        selected_range = ""

    start_raw = request.args.get("start_date")
    end_raw = request.args.get("end_date")

    today = date.today()

    def _month_start(d, months_back):
        total = d.month - 1 - months_back
        year = d.year + total // 12
        month = (total % 12) + 1
        return date(year, month, 1)

    def _month_end(d):
        if d.month == 12:
            return date(d.year + 1, 1, 1) - timedelta(days=1)
        return date(d.year, d.month + 1, 1) - timedelta(days=1)

    if selected_range:
        if selected_range == "this_month":
            filter_start = _month_start(today, 0)
            filter_end = _month_end(today)
        elif selected_range == "last_3_months":
            filter_start = _month_start(today, 2)
            filter_end = _month_end(today)
        elif selected_range == "last_6_months":
            filter_start = _month_start(today, 5)
            filter_end = _month_end(today)
        else:  # all_time
            filter_start = None
            filter_end = None
        start_param = filter_start.isoformat() if filter_start else None
        end_param = filter_end.isoformat() if filter_end else None
        form_start = start_param or ""
        form_end = end_param or ""
    else:
        start_param = _parse_iso(start_raw)
        end_param = _parse_iso(end_raw)
        form_start = start_param or ""
        form_end = end_param or ""

    expenses = get_expenses_by_user(user_id, start_date=start_param, end_date=end_param)

    filter_active = bool(start_param or end_param)

    # Derived summary values (plain Python, no SQL).
    total_spent = sum((e["amount"] or 0) for e in expenses)
    expense_count = len(expenses)
    category_totals = {}
    for e in expenses:
        category_totals[e["category"]] = category_totals.get(e["category"], 0) + (e["amount"] or 0)
    top_category = max(category_totals, key=category_totals.get) if category_totals else None
    category_breakdown = [
        {"category": c, "total": t}
        for c, t in sorted(category_totals.items(), key=lambda kv: kv[1], reverse=True)
    ]

    return render_template(
        "profile.html",
        user=user,
        expenses=expenses,
        total_spent=total_spent,
        expense_count=expense_count,
        top_category=top_category,
        category_breakdown=category_breakdown,
        selected_range=selected_range,
        form_start=form_start,
        form_end=form_end,
        filter_active=filter_active,
    )


@app.route("/analytics")
def analytics():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    return render_template("analytics.html", user=user)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    categories = CATEGORIES

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            user=user,
            categories=categories,
            error=None,
            form={"amount": "", "category": "", "date": date.today().isoformat(), "description": ""},
        )

    error, amount, category, expense_date, description, form_data = _validate_expense_form(
        request.form, categories
    )

    if error:
        return render_template(
            "add_expense.html",
            user=user,
            categories=categories,
            error=error,
            form=form_data,
        )

    create_expense(user_id, amount, category, expense_date, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None or expense["user_id"] != user_id:
        abort(404)

    categories = CATEGORIES

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            user=user,
            categories=categories,
            expense=expense,
            error=None,
            form={
                "amount": expense["amount"],
                "category": expense["category"],
                "date": expense["date"],
                "description": expense["description"] if expense["description"] is not None else "",
            },
        )

    error, amount, category, expense_date, description, form_data = _validate_expense_form(
        request.form, categories
    )

    if error:
        return render_template(
            "edit_expense.html",
            user=user,
            categories=categories,
            expense=expense,
            error=error,
            form=form_data,
        )

    update_expense(id, amount, category, expense_date, description, user_id=user_id)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", endpoint="delete_expense")
def delete_expense_view(id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None or expense["user_id"] != user_id:
        abort(404)

    delete_expense(id, user_id=user_id)
    return redirect(url_for("profile"))


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
