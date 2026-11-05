import os
import tempfile
from pathlib import Path

import pytest

from app import app as flask_app
from database.db import (
    init_db,
    get_db,
    get_user_by_email,
)

REGISTER_DATA = {
    "name": "Test User",
    "email": "test@example.com",
    "password": "password123",
    "confirm_password": "password123",
}

VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health",
                    "Entertainment", "Shopping", "Other"]


@pytest.fixture
def app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    import database.db as db_module

    db_module.DB_PATH = Path(path)

    flask_app.config.update(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret",
        }
    )
    with flask_app.app_context():
        init_db()
        yield flask_app

    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/register", data=REGISTER_DATA)
    client.post(
        "/login",
        data={"email": REGISTER_DATA["email"], "password": REGISTER_DATA["password"]},
    )
    return client


def _user_id(email=REGISTER_DATA["email"]):
    row = get_user_by_email(email)
    assert row is not None, "expected registered user to exist"
    return row["id"]


def _expense_count(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def _latest_expense(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    finally:
        conn.close()


class TestAddExpenseAuth:
    def test_get_unauthenticated_redirects_to_login(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    def test_post_unauthenticated_redirects_to_login(self, client):
        response = client.post(
            "/expenses/add",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


class TestAddExpenseGet:
    def test_get_authenticated_returns_200(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert response.status_code == 200

    def test_get_renders_form(self, auth_client):
        response = auth_client.get("/expenses/add")
        assert b"<form" in response.data
        assert b'name="amount"' in response.data
        assert b'name="category"' in response.data
        assert b'name="date"' in response.data
        assert b'name="description"' in response.data

    def test_get_renders_all_categories(self, auth_client):
        response = auth_client.get("/expenses/add")
        for c in VALID_CATEGORIES:
            assert c.encode() in response.data


class TestAddExpensePostValid:
    def test_valid_post_redirects_to_profile(self, auth_client):
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "42.5",
                "category": "Food",
                "date": "2024-01-10",
                "description": "Lunch",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")

    def test_valid_post_persists_row(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        auth_client.post(
            "/expenses/add",
            data={
                "amount": "42.5",
                "category": "Food",
                "date": "2024-01-10",
                "description": "Lunch",
            },
        )
        after = _expense_count(uid)
        assert after == before + 1

    def test_valid_post_row_has_submitted_values(self, auth_client):
        uid = _user_id()
        auth_client.post(
            "/expenses/add",
            data={
                "amount": "42.5",
                "category": "Food",
                "date": "2024-01-10",
                "description": "Lunch",
            },
        )
        row = _latest_expense(uid)
        assert row is not None
        assert row["amount"] == pytest.approx(42.5)
        assert row["category"] == "Food"
        assert row["date"] == "2024-01-10"
        assert row["description"] == "Lunch"
        assert row["user_id"] == uid

    def test_profile_shows_new_expense_after_post(self, auth_client):
        auth_client.post(
            "/expenses/add",
            data={
                "amount": "42.5",
                "category": "Food",
                "date": "2024-01-10",
                "description": "LUNCH_DESC",
            },
        )
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"LUNCH_DESC" in response.data
        assert b"Food" in response.data
        assert b"2024-01-10" in response.data

    def test_profile_summary_reflects_new_expense(self, auth_client):
        auth_client.post(
            "/expenses/add",
            data={
                "amount": "42.5",
                "category": "Food",
                "date": "2024-01-10",
                "description": "Lunch",
            },
        )
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"42.5" in response.data


class TestAddExpenseOptionalDescription:
    def test_empty_description_allowed(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "5.0",
                "category": "Other",
                "date": "2024-02-02",
                "description": "",
            },
        )
        assert response.status_code == 302
        assert _expense_count(uid) == before + 1
        row = _latest_expense(uid)
        assert row["description"] is None

    def test_missing_description_field_allowed(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "5.0",
                "category": "Other",
                "date": "2024-02-02",
            },
        )
        assert response.status_code == 302
        assert _expense_count(uid) == before + 1

    def test_empty_description_renders_on_profile(self, auth_client):
        auth_client.post(
            "/expenses/add",
            data={
                "amount": "5.0",
                "category": "Other",
                "date": "2024-02-02",
                "description": "",
            },
        )
        response = auth_client.get("/profile")
        assert response.status_code == 200


class TestAddExpenseValidation:
    def test_missing_amount_rejected(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        assert b"Amount is required" in response.data
        assert _expense_count(uid) == before

    def test_invalid_amount_rejected(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "not-a-number",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        assert _expense_count(uid) == before

    def test_negative_amount_rejected(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "-5",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        assert _expense_count(uid) == before

    def test_invalid_category_rejected(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "10.0",
                "category": "Bogus",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        assert _expense_count(uid) == before

    def test_invalid_date_rejected(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "not-a-date",
                "description": "x",
            },
        )
        assert response.status_code == 200
        assert _expense_count(uid) == before

    def test_missing_date_rejected(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "",
                "description": "x",
            },
        )
        assert response.status_code == 200
        assert _expense_count(uid) == before

    def test_validation_preserves_submitted_values(self, auth_client):
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "not-a-number",
                "category": "Food",
                "date": "2024-01-10",
                "description": "KEEP_ME",
            },
        )
        assert response.status_code == 200
        assert b"not-a-number" in response.data
        assert b"KEEP_ME" in response.data

    def test_validation_shows_error_message(self, auth_client):
        response = auth_client.post(
            "/expenses/add",
            data={
                "amount": "",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        assert b"Amount is required" in response.data


class TestAddExpenseDBSideEffects:
    def test_failed_validation_does_not_insert_partial_row(self, auth_client):
        uid = _user_id()
        before = _expense_count(uid)
        auth_client.post(
            "/expenses/add",
            data={
                "amount": "10.0",
                "category": "Bogus",
                "date": "not-a-date",
                "description": "x",
            },
        )
        assert _expense_count(uid) == before

    def test_create_expense_via_route_returns_row_id(self, auth_client):
        uid = _user_id()
        auth_client.post(
            "/expenses/add",
            data={
                "amount": "7.25",
                "category": "Health",
                "date": "2024-03-03",
                "description": "Med",
            },
        )
        row = _latest_expense(uid)
        assert row["id"] is not None

    def test_only_current_user_gets_expense(self, auth_client):
        uid = _user_id()
        auth_client.post(
            "/expenses/add",
            data={
                "amount": "9.0",
                "category": "Food",
                "date": "2024-01-01",
                "description": "mine",
            },
        )
        rows = get_db().execute(
            "SELECT user_id FROM expenses"
        ).fetchall()
        assert all(r["user_id"] is not None for r in rows)
        assert any(r["user_id"] == uid for r in rows)
