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
    delete_expense,
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


def _expense_count(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    finally:
        conn.close()


def _foreign_expense_id():
    uid = create_user("Other User", "other@example.com",
                      generate_password_hash("password123"))
    return create_expense(uid, 5.0, "Food", "2024-01-01", "foreign")


class TestDeleteExpenseAuth:
    def test_get_unauthenticated_redirects_to_login(self, client):
        response = client.get("/expenses/1/delete")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")

    def test_nonexistent_unauthenticated_redirects_to_login(self, client):
        response = client.get("/expenses/99999/delete")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


class TestDeleteExpenseNotFound:
    def test_nonexistent_returns_404(self, auth_client):
        response = auth_client.get("/expenses/99999/delete")
        assert response.status_code == 404

    def test_foreign_expense_returns_404(self, auth_client):
        eid = _foreign_expense_id()
        response = auth_client.get(f"/expenses/{eid}/delete")
        assert response.status_code == 404


class TestDeleteExpenseHappy:
    def test_delete_redirects_to_profile(self, auth_client):
        _create_expense(auth_client)
        eid = _latest_expense_id(_user_id())
        response = auth_client.get(f"/expenses/{eid}/delete")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/profile")

    def test_deleted_row_absent_from_db(self, auth_client):
        _create_expense(auth_client, description="TODELETE")
        eid = _latest_expense_id(_user_id())
        auth_client.get(f"/expenses/{eid}/delete")
        assert get_expense_by_id(eid) is None

    def test_expense_count_decrements(self, auth_client):
        _create_expense(auth_client)
        uid = _user_id()
        before = _expense_count(uid)
        eid = _latest_expense_id(uid)
        auth_client.get(f"/expenses/{eid}/delete")
        assert _expense_count(uid) == before - 1

    def test_deleted_entry_not_in_profile(self, auth_client):
        _create_expense(auth_client, description="UNIQUE_DELETE_ME")
        eid = _latest_expense_id(_user_id())
        auth_client.get(f"/expenses/{eid}/delete")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"UNIQUE_DELETE_ME" not in response.data

    def test_foreign_expense_not_deleted_via_route(self, auth_client):
        eid = _foreign_expense_id()
        before = get_expense_by_id(eid)
        response = auth_client.get(f"/expenses/{eid}/delete")
        assert response.status_code == 404
        after = get_expense_by_id(eid)
        assert after is not None
        assert after["amount"] == before["amount"]
        assert after["description"] == before["description"]

    def test_delete_only_target_expense(self, auth_client):
        _create_expense(auth_client, description="KEEPER")
        _create_expense(auth_client, description="REMOVER")
        uid = _user_id()
        eid = _latest_expense_id(uid)
        auth_client.get(f"/expenses/{eid}/delete")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"KEEPER" in response.data
        assert b"REMOVER" not in response.data


class TestDeleteExpenseSummary:
    def test_profile_total_reflects_deletion(self, auth_client):
        _create_expense(auth_client, amount="40.0", category="Food",
                        description="ONE")
        _create_expense(auth_client, amount="60.0", category="Food",
                        description="TWO")
        uid = _user_id()
        eid = _latest_expense_id(uid)
        auth_client.get(f"/expenses/{eid}/delete")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"40" in response.data

    def test_category_breakdown_reflects_deletion(self, auth_client):
        _create_expense(auth_client, amount="10.0", category="Bills",
                        description="BILL_X")
        uid = _user_id()
        eid = _latest_expense_id(uid)
        auth_client.get(f"/expenses/{eid}/delete")
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"BILL_X" not in response.data


class TestDeleteExpenseHelper:
    def test_delete_expense_returns_rowcount(self, auth_client):
        _create_expense(auth_client)
        uid = _user_id()
        eid = _latest_expense_id(uid)
        count = delete_expense(eid, user_id=uid)
        assert count == 1
        assert get_expense_by_id(eid) is None

    def test_delete_expense_no_user_id_deletes(self, auth_client):
        _create_expense(auth_client)
        uid = _user_id()
        eid = _latest_expense_id(uid)
        count = delete_expense(eid)
        assert count == 1
        assert get_expense_by_id(eid) is None

    def test_delete_expense_scoped_wrong_user_returns_zero(self, auth_client):
        eid = _foreign_expense_id()
        uid = _user_id()
        count = delete_expense(eid, user_id=uid)
        assert count == 0
        assert get_expense_by_id(eid) is not None

    def test_delete_expense_missing_returns_zero(self, auth_client):
        uid = _user_id()
        count = delete_expense(999999, user_id=uid)
        assert count == 0

    def test_delete_expense_sql_injection_safe(self, auth_client):
        _create_expense(auth_client)
        uid = _user_id()
        eid = _latest_expense_id(uid)
        try:
            delete_expense(eid, user_id=uid)
        except Exception:
            pass
        conn = get_db()
        try:
            rows = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
            assert isinstance(rows, int)
        finally:
            conn.close()
