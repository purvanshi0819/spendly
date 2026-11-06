import os
import tempfile
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import (
    init_db,
    get_db,
    get_user_by_email,
    create_user,
    create_expense,
    get_expense_by_id,
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


def _create_expense(client, amount="10.0", category="Food", date="2024-01-10",
                    description="orig"):
    client.post(
        "/expenses/add",
        data={
            "amount": amount,
            "category": category,
            "date": date,
            "description": description,
        },
    )


def _latest_expense_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        assert row is not None, "expected an expense to exist"
        return row["id"]
    finally:
        conn.close()


def _foreign_expense_id():
    uid = create_user("Other User", "other@example.com",
                      generate_password_hash("password123"))
    return create_expense(uid, 5.0, "Food", "2024-01-01", "foreign")


class TestEditExpenseAuth:
    def test_get_unauthenticated_redirects_to_login(self, client):
        response = client.get("/expenses/1/edit")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    def test_post_unauthenticated_redirects_to_login(self, client):
        response = client.post(
            "/expenses/1/edit",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


class TestEditExpenseNotFound:
    def test_get_nonexistent_returns_404(self, auth_client):
        response = auth_client.get("/expenses/99999/edit")
        assert response.status_code == 404

    def test_post_nonexistent_returns_404(self, auth_client):
        response = auth_client.post(
            "/expenses/99999/edit",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 404

    def test_get_foreign_expense_returns_404(self, auth_client):
        eid = _foreign_expense_id()
        response = auth_client.get(f"/expenses/{eid}/edit")
        assert response.status_code == 404

    def test_post_foreign_expense_returns_404(self, auth_client):
        eid = _foreign_expense_id()
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 404


class TestEditExpenseGet:
    def test_get_authenticated_returns_200(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.get(f"/expenses/{eid}/edit")
        assert response.status_code == 200

    def test_get_renders_form(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.get(f"/expenses/{eid}/edit")
        assert b"<form" in response.data
        assert b'name="amount"' in response.data
        assert b'name="category"' in response.data
        assert b'name="date"' in response.data
        assert b'name="description"' in response.data

    def test_get_renders_all_categories(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.get(f"/expenses/{eid}/edit")
        for c in VALID_CATEGORIES:
            assert c.encode() in response.data

    def test_get_prefills_stored_values(self, auth_client):
        _create_expense(auth_client, amount="42.5", category="Food",
                        date="2024-01-10", description="origdesc")
        eid = _latest_expense_id(_user_id())
        response = auth_client.get(f"/expenses/{eid}/edit")
        assert response.status_code == 200
        assert b"42.5" in response.data
        assert b"origdesc" in response.data
        assert b"2024-01-10" in response.data

    def test_get_prefills_empty_description_as_empty(self, auth_client):
        _create_expense(auth_client, amount="5.0", category="Other",
                        date="2024-02-02", description="")
        eid = _latest_expense_id(_user_id())
        response = auth_client.get(f"/expenses/{eid}/edit")
        assert response.status_code == 200

    def test_get_has_cancel_link_profile(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.get(f"/expenses/{eid}/edit")
        assert b"/profile" in response.data


class TestEditExpensePostValid:
    def test_valid_post_redirects_to_profile(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "99.9",
                "category": "Transport",
                "date": "2024-02-20",
                "description": "updated",
            },
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")

    def test_valid_post_persists_update(self, auth_client):
        _create_expense(auth_client, amount="10.0", category="Food",
                        date="2024-01-10", description="orig")
        eid = _latest_expense_id(_user_id())
        auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "99.9",
                "category": "Transport",
                "date": "2024-02-20",
                "description": "updated",
            },
        )
        row = get_expense_by_id(eid)
        assert row is not None
        assert row["amount"] == pytest.approx(99.9)
        assert row["category"] == "Transport"
        assert row["date"] == "2024-02-20"
        assert row["description"] == "updated"

    def test_valid_post_user_id_unchanged(self, auth_client):
        _create_expense(auth_client)
        uid = _user_id()
        eid = _latest_expense_id(uid)
        auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "7.0",
                "category": "Health",
                "date": "2024-03-03",
                "description": "x",
            },
        )
        row = get_expense_by_id(eid)
        assert row["user_id"] == uid

    def test_profile_shows_updated_expense_after_post(self, auth_client):
        _create_expense(auth_client, amount="10.0", category="Food",
                        date="2024-01-10", description="origdesc")
        eid = _latest_expense_id(_user_id())
        auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "99.9",
                "category": "Transport",
                "date": "2024-02-20",
                "description": "NEWDESC",
            },
        )
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"NEWDESC" in response.data
        assert b"Transport" in response.data
        assert b"2024-02-20" in response.data

    def test_profile_summary_reflects_updated_values(self, auth_client):
        _create_expense(auth_client, amount="10.0", category="Food",
                        date="2024-01-10", description="orig")
        eid = _latest_expense_id(_user_id())
        auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "99.9",
                "category": "Transport",
                "date": "2024-02-20",
                "description": "updated",
            },
        )
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Transport" in response.data


class TestEditExpenseOptionalDescription:
    def test_empty_description_allowed(self, auth_client):
        _create_expense(auth_client, amount="10.0", category="Food",
                        date="2024-01-10", description="orig")
        eid = _latest_expense_id(_user_id())
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "5.0",
                "category": "Other",
                "date": "2024-02-02",
                "description": "",
            },
        )
        assert response.status_code == 302
        row = get_expense_by_id(eid)
        assert row["description"] is None

    def test_missing_description_field_allowed(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "5.0",
                "category": "Other",
                "date": "2024-02-02",
            },
        )
        assert response.status_code == 302
        row = get_expense_by_id(eid)
        assert row["description"] is None

    def test_description_to_none_persists(self, auth_client):
        _create_expense(auth_client, description="something")
        eid = _latest_expense_id(_user_id())
        auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "2024-01-10",
                "description": "",
            },
        )
        row = get_expense_by_id(eid)
        assert row["description"] is None


class TestEditExpenseValidation:
    def test_missing_amount_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        uid = _user_id()
        before = (get_expense_by_id(eid)["amount"])
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row = get_expense_by_id(eid)
        assert row["amount"] == pytest.approx(before)
        assert b"Amount is required" in response.data

    def test_invalid_amount_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "not-a-number",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["amount"] == pytest.approx(row_before["amount"])
        assert row_after["category"] == row_before["category"]

    def test_negative_amount_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "-5",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["amount"] == pytest.approx(row_before["amount"])

    def test_empty_category_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["category"] == row_before["category"]

    def test_invalid_category_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "Bogus",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["category"] == row_before["category"]

    def test_invalid_date_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "not-a-date",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["date"] == row_before["date"]

    def test_missing_date_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["date"] == row_before["date"]

    def test_description_too_long_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x" * 501,
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["description"] == row_before["description"]
        assert row_after["amount"] == pytest.approx(row_before["amount"])

    def test_amount_too_long_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "1" * 21,
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["amount"] == pytest.approx(row_before["amount"])

    def test_category_too_long_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        row_before = get_expense_by_id(eid)
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "A" * 31,
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        row_after = get_expense_by_id(eid)
        assert row_after["category"] == row_before["category"]

    def test_validation_preserves_submitted_values(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.post(
            f"/expenses/{eid}/edit",
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
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200
        assert b"Amount is required" in response.data

    def test_failed_validation_does_not_update(self, auth_client):
        _create_expense(auth_client, amount="10.0", category="Food",
                        date="2024-01-10", description="orig")
        eid = _latest_expense_id(_user_id())
        auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "Bogus",
                "date": "not-a-date",
                "description": "x",
            },
        )
        row = get_expense_by_id(eid)
        assert row["amount"] == pytest.approx(10.0)
        assert row["category"] == "Food"
        assert row["date"] == "2024-01-10"
        assert row["description"] == "orig"

    def test_inf_amount_rejected(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "Infinity",
                "category": "Food",
                "date": "2024-01-10",
                "description": "x",
            },
        )
        assert response.status_code == 200


class TestEditExpenseDBHelpers:
    def test_get_expense_by_id_returns_none_missing(self, auth_client):
        assert get_expense_by_id(999999) is None

    def test_get_expense_by_id_returns_row(self, auth_client):
        _create_expense(auth_client, amount="7.7", category="Health",
                        date="2024-03-03", description="hd")
        eid = _latest_expense_id(_user_id())
        row = get_expense_by_id(eid)
        assert row is not None
        assert row["amount"] == pytest.approx(7.7)
        assert row["category"] == "Health"

    def test_update_expense_sql_injection_safe(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        from database.db import update_expense
        update_expense(eid, 1.0, "Food'; DROP TABLE expenses;--", "2024-01-01", "d")
        # category invalid but row persisted as literal (helper doesn't validate)
        row = get_expense_by_id(eid)
        assert row is not None

    def test_foreign_expense_not_updated_via_route(self, auth_client):
        eid = _foreign_expense_id()
        # direct check that route returns 404 and leaves row intact
        before = get_expense_by_id(eid)
        resp = auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "1.0",
                "category": "Food",
                "date": "2024-01-01",
                "description": "hack",
            },
        )
        assert resp.status_code == 404
        after = get_expense_by_id(eid)
        assert after["amount"] == pytest.approx(before["amount"])
        assert after["description"] == before["description"]


class TestEditExpenseSummaryStats:
    def test_category_breakdown_reflects_update(self, auth_client):
        _create_expense(auth_client, amount="10.0", category="Food",
                        date="2024-01-10", description="orig")
        eid = _latest_expense_id(_user_id())
        auth_client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "10.0",
                "category": "Bills",
                "date": "2024-01-10",
                "description": "orig",
            },
        )
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Bills" in response.data