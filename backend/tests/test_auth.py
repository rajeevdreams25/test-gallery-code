"""Accounts and authentication — FR-1..FR-9, AC-1..AC-5."""

import jwt
import pytest

from app.config import settings
from app.security import create_access_token


class TestRegister:
    def test_register_returns_token_and_user(self, client):
        """FR-1, FR-4, AC-1."""
        response = client.post(
            "/auth/register", json={"email": "new@example.com", "password": "a-good-password"}
        )

        assert response.status_code == 201
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["user"]["email"] == "new@example.com"
        assert isinstance(body["user"]["id"], int)

        header = jwt.get_unverified_header(body["access_token"])
        assert header["alg"] == "HS256"

    def test_issued_token_authenticates_immediately(self, client):
        """FR-4, FR-9 — registration logs the new user straight in."""
        token = client.post(
            "/auth/register", json={"email": "fresh@example.com", "password": "a-good-password"}
        ).json()["access_token"]

        me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

        assert me.status_code == 200
        assert me.json()["email"] == "fresh@example.com"

    def test_password_is_never_returned_or_stored_in_clear(self, client):
        """FR-3 — bcrypt hash only, nothing in the response or the row."""
        from sqlalchemy.orm import Session

        from app.database import engine
        from app.models import User

        password = "hunter2-hunter2"
        response = client.post(
            "/auth/register", json={"email": "quiet@example.com", "password": password}
        )

        assert password not in response.text
        assert "password" not in response.json()["user"]

        with Session(engine) as session:
            stored = session.get(User, response.json()["user"]["id"]).hashed_password
        assert password not in stored
        assert stored.startswith("$2b$")

    def test_duplicate_email_is_refused(self, client, alice):
        """FR-2, AC-2."""
        response = client.post(
            "/auth/register", json={"email": alice.email, "password": "another-password"}
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "Email already registered"

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({"email": "not-an-email", "password": "a-good-password"}, id="bad-email"),
            pytest.param({"email": "short@example.com", "password": "short7"}, id="password-too-short"),
            pytest.param({"email": "nopw@example.com"}, id="missing-password"),
            pytest.param({"password": "a-good-password"}, id="missing-email"),
        ],
    )
    def test_malformed_registrations_are_rejected(self, client, payload):
        """FR-1 — the 8-character minimum and the email format are enforced (422)."""
        assert client.post("/auth/register", json=payload).status_code == 422

    def test_password_at_the_bcrypt_limit_round_trips(self, client):
        """FR-1, FR-3 — 72 bytes is the documented maximum; it must still log in."""
        password = "x" * 72
        register = client.post(
            "/auth/register", json={"email": "long@example.com", "password": password}
        )

        assert register.status_code == 201
        login = client.post(
            "/auth/login", json={"email": "long@example.com", "password": password}
        )
        assert login.status_code == 200


class TestLogin:
    def test_correct_credentials_return_a_token(self, client, alice):
        """FR-4."""
        response = client.post(
            "/auth/login", json={"email": alice.email, "password": alice.password}
        )

        assert response.status_code == 200
        assert response.json()["user"]["id"] == alice.id
        assert response.json()["access_token"]

    def test_wrong_password_is_refused(self, client, alice):
        """FR-5, AC-3."""
        response = client.post(
            "/auth/login", json={"email": alice.email, "password": "not-the-password"}
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password"

    def test_failure_message_does_not_reveal_which_field_was_wrong(self, client, alice):
        """FR-5 — no account enumeration through the login response."""
        wrong_password = client.post(
            "/auth/login", json={"email": alice.email, "password": "not-the-password"}
        )
        unknown_email = client.post(
            "/auth/login", json={"email": "ghost@example.com", "password": "not-the-password"}
        )

        assert unknown_email.status_code == wrong_password.status_code == 401
        assert unknown_email.json()["detail"] == wrong_password.json()["detail"]


class TestTokenGuard:
    def test_protected_endpoint_without_a_token(self, client):
        """FR-8, AC-4."""
        assert client.get("/auth/me").status_code == 401
        assert client.get("/images").status_code == 401

    @pytest.mark.parametrize(
        "header",
        [
            pytest.param("Bearer not.a.jwt", id="corrupted"),
            pytest.param("Bearer ", id="empty"),
            pytest.param("Basic dXNlcjpwYXNz", id="wrong-scheme"),
        ],
    )
    def test_malformed_tokens_are_refused(self, client, header):
        """FR-8, AC-5."""
        assert client.get("/images", headers={"Authorization": header}).status_code == 401

    def test_token_signed_with_another_key_is_refused(self, client, alice):
        """FR-8 — the signature, not just the shape, is verified."""
        forged = jwt.encode({"sub": str(alice.id)}, "some-other-key", algorithm=settings.algorithm)

        assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401

    def test_expired_token_is_refused(self, client, alice, monkeypatch):
        """FR-6, FR-8."""
        monkeypatch.setattr(settings, "access_token_expire_minutes", -1)
        expired = create_access_token(alice.id)

        assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    def test_default_token_lifetime_is_sixty_minutes(self, alice):
        """FR-6 — the default expiry is 60 minutes."""
        claims = jwt.decode(alice.token, settings.secret_key, algorithms=[settings.algorithm])

        assert settings.access_token_expire_minutes == 60
        assert "exp" in claims
        assert claims["sub"] == str(alice.id)

    def test_token_for_a_deleted_account_is_refused(self, client, alice):
        """FR-8 — a token alone is not enough; the account must still exist."""
        from sqlalchemy.orm import Session

        from app.database import engine
        from app.models import User

        with Session(engine) as session:
            session.delete(session.get(User, alice.id))
            session.commit()

        assert client.get("/auth/me", headers=alice.headers).status_code == 401

    def test_me_returns_the_caller_not_another_user(self, client, alice, bob):
        """FR-9, NFR-2."""
        assert client.get("/auth/me", headers=alice.headers).json()["id"] == alice.id
        assert client.get("/auth/me", headers=bob.headers).json()["id"] == bob.id
