import os
import tempfile
from pathlib import Path
from datetime import date, timedelta

import pytest
from flask import url_for

from app import app as flask_app
from database.db import init_db, get_db, get_user_by_email


REGISTER_DATA = {
    "name": "Test User",
    "email": "test@example.com",
    "password": "password123",
    "confirm_password": "password123",
}


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


def _add_expense(user_id, amount, category, date_str, description=None):
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO expenses (user_id, amount, category, date, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, amount, category, date_str, description),
        )
        conn.commit()
    finally:
        conn.close()


class TestProfileAuth:
    def test_profile_unauthenticated_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, "unauthenticated /profile should redirect"
        assert response.headers["Location"].endswith("/login")

    def test_profile_unauthenticated_with_query_params_redirects_to_login(self, client):
        response = client.get(
            "/profile?start_date=2024-01-01&end_date=2024-02-01&range=this_month"
        )
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


class TestProfileNoFilter:
    def test_profile_logged_in_returns_200(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200

    def test_profile_empty_list_shows_empty_state(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"No expenses yet" in response.data


class TestProfileDateRange:
    def setup_method(self):
        # Data is inserted per test through helpers; nothing shared.
        pass

    def test_profile_with_valid_range_returns_200(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        _add_expense(uid, 200.0, "Transport", "2024-03-15", "MAR_EXP")

        response = auth_client.get(
            "/profile?start_date=2024-01-01&end_date=2024-12-31"
        )
        assert response.status_code == 200
        assert b"MAR_EXP" in response.data

    def test_profile_range_filters_expenses_inclusively(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        _add_expense(uid, 200.0, "Transport", "2024-03-15", "MAR_EXP")
        _add_expense(uid, 300.0, "Bills", "2024-06-20", "JUN_EXP")

        response = auth_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-04-30"
        )
        assert response.status_code == 200
        assert b"MAR_EXP" in response.data, "in-range expense should be listed"
        assert b"JAN_EXP" not in response.data, "before-range expense excluded"
        assert b"JUN_EXP" not in response.data, "after-range expense excluded"

    def test_profile_start_and_end_boundaries_are_inclusive(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 50.0, "Food", "2024-05-01", "BOUNDARY_START")
        _add_expense(uid, 60.0, "Food", "2024-05-31", "BOUNDARY_END")
        _add_expense(uid, 70.0, "Food", "2024-05-15", "MIDDLE")

        response = auth_client.get(
            "/profile?start_date=2024-05-01&end_date=2024-05-31"
        )
        assert response.status_code == 200
        assert b"BOUNDARY_START" in response.data
        assert b"BOUNDARY_END" in response.data
        assert b"MIDDLE" in response.data

    def test_profile_stats_reflect_filtered_set(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        _add_expense(uid, 200.0, "Transport", "2024-03-15", "MAR_EXP")
        _add_expense(uid, 300.0, "Bills", "2024-06-20", "JUN_EXP")

        response = auth_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-04-30"
        )
        assert response.status_code == 200
        # Only the 200.0 expense is in range.
        assert b"200.0" in response.data, "filtered total should appear"
        assert b"Transport" in response.data, "filtered category should appear"
        assert b"Bills" not in response.data, "excluded category not in breakdown"

    def test_profile_start_date_only_filters_lower_bound(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        _add_expense(uid, 200.0, "Transport", "2024-03-15", "MAR_EXP")

        response = auth_client.get("/profile?start_date=2024-02-01")
        assert response.status_code == 200
        assert b"MAR_EXP" in response.data
        assert b"JAN_EXP" not in response.data

    def test_profile_end_date_only_filters_upper_bound(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        _add_expense(uid, 200.0, "Transport", "2024-03-15", "MAR_EXP")

        response = auth_client.get("/profile?end_date=2024-02-01")
        assert response.status_code == 200
        assert b"JAN_EXP" in response.data
        assert b"MAR_EXP" not in response.data

    def test_profile_inverted_range_returns_empty(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        _add_expense(uid, 200.0, "Transport", "2024-03-15", "MAR_EXP")

        response = auth_client.get(
            "/profile?start_date=2024-06-01&end_date=2024-02-01"
        )
        assert response.status_code == 200
        assert b"No expenses yet" in response.data

    def test_profile_invalid_date_does_not_error(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")

        response = auth_client.get(
            "/profile?start_date=not-a-date&end_date=also-invalid"
        )
        assert response.status_code == 200
        # Invalid inputs are treated as no bound, so the row survives.
        assert b"JAN_EXP" in response.data

    def test_profile_empty_date_params_do_not_error(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")

        response = auth_client.get("/profile?start_date=&end_date=")
        assert response.status_code == 200
        assert b"JAN_EXP" in response.data

    def test_profile_filter_does_not_modify_database(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        _add_expense(uid, 200.0, "Transport", "2024-03-15", "MAR_EXP")

        before = get_db().execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (uid,)
        ).fetchone()[0]
        auth_client.get("/profile?start_date=2024-02-01&end_date=2024-04-30")
        after = get_db().execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (uid,)
        ).fetchone()[0]
        assert before == after == 2


class TestProfilePresets:
    def test_preset_this_month_returns_200(self, auth_client):
        response = auth_client.get("/profile?range=this_month")
        assert response.status_code == 200

    def test_preset_last_3_months_returns_200(self, auth_client):
        response = auth_client.get("/profile?range=last_3_months")
        assert response.status_code == 200

    def test_preset_last_6_months_returns_200(self, auth_client):
        response = auth_client.get("/profile?range=last_6_months")
        assert response.status_code == 200

    def test_preset_all_time_returns_200(self, auth_client):
        response = auth_client.get("/profile?range=all_time")
        assert response.status_code == 200

    def test_invalid_range_falls_back_to_no_range(self, auth_client):
        response = auth_client.get("/profile?range=bogus")
        assert response.status_code == 200

    def test_preset_this_month_filters_to_current_month(self, auth_client):
        uid = _user_id()
        today = date.today()
        current_desc = "THIS_MONTH_EXP"
        old_desc = "OLD_EXP"
        _add_expense(uid, 10.0, "Food", today.isoformat(), current_desc)
        _add_expense(
            uid,
            20.0,
            "Food",
            (today - timedelta(days=400)).isoformat(),
            old_desc,
        )

        response = auth_client.get("/profile?range=this_month")
        assert response.status_code == 200
        assert current_desc.encode() in response.data
        assert old_desc.encode() not in response.data

    def test_range_takes_precedence_over_manual_dates(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2020-01-10", "OLD_MANUAL")

        month_start = date(date.today().year, date.today().month, 1).isoformat()

        response = auth_client.get(
            "/profile?range=this_month&start_date=2020-01-01&end_date=2020-01-31"
        )
        assert response.status_code == 200
        # Preset-derived bound is surfaced, not the manual one.
        assert month_start.encode() in response.data
        assert b"2020-01-01" not in response.data


class TestProfileFilterState:
    def test_profile_preserves_start_date_value(self, auth_client):
        response = auth_client.get(
            "/profile?start_date=2024-02-01&end_date=2024-04-30"
        )
        assert response.status_code == 200
        assert b'value="2024-02-01"' in response.data
        assert b'value="2024-04-30"' in response.data

    def test_clear_filter_link_present_when_filter_active(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        response = auth_client.get("/profile?start_date=2024-01-01&end_date=2024-12-31")
        assert response.status_code == 200
        assert b"Clear filter" in response.data

    def test_clear_filter_link_absent_when_no_filter(self, auth_client):
        response = auth_client.get("/profile")
        assert response.status_code == 200
        assert b"Clear filter" not in response.data

    def test_clear_filter_resets_to_full_list(self, auth_client):
        uid = _user_id()
        _add_expense(uid, 100.0, "Food", "2024-01-10", "JAN_EXP")
        _add_expense(uid, 200.0, "Transport", "2024-03-15", "MAR_EXP")

        filtered = auth_client.get("/profile?start_date=2024-02-01&end_date=2024-04-30")
        assert b"MAR_EXP" in filtered.data
        assert b"JAN_EXP" not in filtered.data

        cleared = auth_client.get("/profile")
        assert b"JAN_EXP" in cleared.data
        assert b"MAR_EXP" in cleared.data

    def test_unauthenticated_clear_or_filter_redirects(self, client):
        response = client.get("/profile?start_date=2024-01-01")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")