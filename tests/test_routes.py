import os
import tempfile
import unittest
from importlib.metadata import version

import werkzeug


if not hasattr(werkzeug, "__version__"):
    werkzeug.__version__ = version("werkzeug")


TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="qual-coder-auth-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DIRECTORY.name}/test.db"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["APP_ORIGINS"] = "http://localhost"

from app import app
from models import Coder, Project, ProjectMembership, User, db


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

            self.project = Project(name="Private Study", slug="private-study", codebook="[]")
            self.other_project = Project(name="Other Study", slug="other-study", codebook="[]")
            db.session.add_all([self.project, self.other_project])
            db.session.flush()

            self.alice_coder = Coder(name="Alice Coder", project_id=self.project.id)
            self.other_coder = Coder(name="Other Coder", project_id=self.project.id)
            db.session.add_all([self.alice_coder, self.other_coder])
            db.session.flush()

            admin = User(username="admin", display_name="Administrator", is_admin=True, is_active=True, must_change_password=False)
            admin.set_password("admin-password-123")
            researcher = User(username="alice", display_name="Alice Researcher", is_active=True, must_change_password=False)
            researcher.set_password("alice-password-123")
            db.session.add_all([admin, researcher])
            db.session.flush()
            db.session.add(ProjectMembership(
                user_id=researcher.id,
                project_id=self.project.id,
                coder_id=self.alice_coder.id,
                role="researcher",
            ))
            db.session.commit()

    def login(self, username, password):
        response = self.client.post("/auth/login", json={
            "username": username,
            "password": password,
        })
        return response, response.get_json().get("csrf_token") if response.is_json else None

    def test_anonymous_project_listing_is_denied(self):
        response = self.client.get("/projects")
        self.assertEqual(response.status_code, 401)

    def test_anonymous_access_is_denied_across_research_routes(self):
        requests = [
            ("get", "/project-info?project=private-study", None),
            ("get", "/download-codebook?project=private-study", None),
            ("get", "/download-results?project=private-study", None),
            ("get", "/video-at-index?project=private-study&coder=Alice%20Coder&index=0", None),
            ("post", "/projects", {"name": "Blocked"}),
            ("put", "/project/private-study", {"name": "Blocked"}),
            ("delete", "/project/private-study", None),
            ("post", "/save-progress", {}),
            ("post", "/submit", {}),
            ("post", "/codebook", {}),
            ("get", "/admin/users", None),
        ]
        for method, path, payload in requests:
            with self.subTest(method=method, path=path):
                response = getattr(self.client, method)(path, json=payload)
                self.assertEqual(response.status_code, 401)

    def test_researcher_sees_only_assigned_projects(self):
        login_response, _ = self.login("alice", "alice-password-123")
        self.assertEqual(login_response.status_code, 200)
        response = self.client.get("/projects")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([project["slug"] for project in response.get_json()], ["private-study"])
        self.assertEqual(response.get_json()[0]["assigned_coder"], "Alice Coder")

    def test_researcher_cannot_impersonate_another_coder(self):
        self.login("alice", "alice-password-123")
        response = self.client.get(
            "/video-at-index",
            query_string={"project": "private-study", "coder": "Other Coder", "index": 0},
        )
        self.assertEqual(response.status_code, 403)

    def test_researcher_cannot_open_an_unassigned_project(self):
        self.login("alice", "alice-password-123")
        response = self.client.get("/project-info?project=other-study")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_mutation_requires_csrf(self):
        self.login("admin", "admin-password-123")
        response = self.client.post("/projects", json={"name": "Blocked", "coders": [], "codebook": []})
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_assigned_researcher(self):
        _, csrf_token = self.login("admin", "admin-password-123")
        response = self.client.post(
            "/admin/users",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "username": "new.user",
                "display_name": "New User",
                "password": "new-user-password",
                "project_access": [{
                    "project_slug": "private-study",
                    "role": "researcher",
                    "coder_name": "Alice Coder",
                }],
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.get_json()["user"]["project_access"][0]["project_slug"],
            "private-study",
        )
        self.assertTrue(response.get_json()["user"]["must_change_password"])

    def test_new_researcher_must_change_initial_password(self):
        _, csrf_token = self.login("admin", "admin-password-123")
        self.client.post(
            "/admin/users",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "username": "new.user",
                "display_name": "New User",
                "password": "new-user-password",
                "project_access": [{
                    "project_slug": "private-study",
                    "role": "researcher",
                    "coder_name": "Alice Coder",
                }],
            },
        )
        login_response, new_csrf = self.login("new.user", "new-user-password")
        self.assertTrue(login_response.get_json()["user"]["must_change_password"])
        self.assertEqual(self.client.get("/projects").status_code, 403)

        changed = self.client.post(
            "/auth/change-password",
            headers={"X-CSRF-Token": new_csrf},
            json={
                "current_password": "new-user-password",
                "new_password": "replacement-password",
            },
        )
        self.assertEqual(changed.status_code, 200)
        self.login("new.user", "replacement-password")
        self.assertEqual(self.client.get("/projects").status_code, 200)

    def test_non_admin_cannot_create_accounts(self):
        _, csrf_token = self.login("alice", "alice-password-123")
        response = self.client.post(
            "/admin/users",
            headers={"X-CSRF-Token": csrf_token},
            json={
                "username": "blocked.user",
                "display_name": "Blocked User",
                "password": "blocked-password",
            },
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
