import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.auth import router as auth_router
from app.api.routes.zone import router as zone_router
from app.core.auth import get_db, hash_password, verify_password
from app.database.database import Base


class AuthenticationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=cls.engine)
        cls.session_factory = sessionmaker(bind=cls.engine, expire_on_commit=False)

        app = FastAPI()
        app.include_router(auth_router)
        app.include_router(zone_router)

        def override_get_db():
            db = cls.session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        Base.metadata.drop_all(bind=cls.engine)
        cls.engine.dispose()

    def setUp(self):
        with self.session_factory() as db:
            db.execute(Base.metadata.tables["user_sessions"].delete())
            db.execute(Base.metadata.tables["users"].delete())
            db.commit()
        self.client.cookies.clear()

    def test_passwords_are_salted_and_verified(self):
        first_hash = hash_password("correct-horse-battery")
        second_hash = hash_password("correct-horse-battery")

        self.assertNotEqual(first_hash, second_hash)
        self.assertTrue(verify_password("correct-horse-battery", first_hash))
        self.assertFalse(verify_password("wrong-password", first_hash))

    def test_registration_login_session_and_logout(self):
        registered = self.client.post(
            "/api/auth/register",
            json={
                "name": "Vision Operator",
                "email": "Operator@Example.com",
                "password": "secure-password-123",
            },
        )

        self.assertEqual(registered.status_code, 201)
        self.assertTrue(registered.cookies.get("vision_session"))
        self.assertIn("httponly", registered.headers["set-cookie"].lower())
        self.assertEqual(
            self.client.get("/api/auth/me").json(),
            {"name": "Vision Operator", "email": "operator@example.com"},
        )

        duplicate = self.client.post(
            "/api/auth/register",
            json={
                "name": "Another Operator",
                "email": "operator@example.com",
                "password": "secure-password-123",
            },
        )
        self.assertEqual(duplicate.status_code, 409)

        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)

        wrong_password = self.client.post(
            "/api/auth/login",
            json={"email": "operator@example.com", "password": "not-the-password"},
        )
        self.assertEqual(wrong_password.status_code, 401)

        logged_in = self.client.post(
            "/api/auth/login",
            json={"email": " OPERATOR@example.com ", "password": "secure-password-123"},
        )
        self.assertEqual(logged_in.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
        self.assertEqual(self.client.get("/api/zone/").status_code, 200)

        self.client.post("/api/auth/logout")
        self.assertEqual(self.client.get("/api/zone/").status_code, 401)

    def test_registration_requires_valid_email_and_minimum_password(self):
        invalid_email = self.client.post(
            "/api/auth/register",
            json={"name": "Operator", "email": "not-an-email", "password": "secure-password"},
        )
        short_password = self.client.post(
            "/api/auth/register",
            json={"name": "Operator", "email": "operator@example.com", "password": "short"},
        )

        self.assertEqual(invalid_email.status_code, 422)
        self.assertEqual(short_password.status_code, 422)

    def test_dashboard_api_requires_authentication(self):
        self.assertEqual(self.client.get("/api/zone/").status_code, 401)


if __name__ == "__main__":
    unittest.main()
