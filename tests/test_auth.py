import tempfile
import unittest
from pathlib import Path

from user_service.repositories import InMemorySessionRepository, JsonUserRepository
from user_service.services import AuthError, AuthService, PasswordHasher


class AuthServiceTest(unittest.TestCase):
    def test_register_and_login(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            users_path = Path(directory) / "users.json"
            service = AuthService(
                user_repository=JsonUserRepository(users_path),
                session_repository=InMemorySessionRepository(),
                password_hasher=PasswordHasher(),
            )

            registered = service.register("student", "secret123", "Студент")
            logged_in = service.login("student", "secret123")

            self.assertEqual("student", registered["user"]["username"])
            self.assertIn("token", logged_in)

    def test_login_with_wrong_password_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            users_path = Path(directory) / "users.json"
            service = AuthService(
                user_repository=JsonUserRepository(users_path),
                session_repository=InMemorySessionRepository(),
                password_hasher=PasswordHasher(),
            )

            service.register("student", "secret123", "Студент")

            with self.assertRaises(AuthError):
                service.login("student", "wrong-pass")


if __name__ == "__main__":
    unittest.main()
