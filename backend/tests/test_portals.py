import json
import os
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8011")


def request(method, path, body=None, token=None, extra_headers=None):
    headers = dict(extra_headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if response.headers.get_content_type() == "application/json" else raw
    except HTTPError as error:
        raw = error.read().decode()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw
        return error.code, payload


class PortalRegressionTests(unittest.TestCase):
    def login(self, role, username, password):
        status, data = request("POST", "/api/v1/auth/login", {"role": role, "username": username, "password": password})
        self.assertEqual(status, 200, data)
        return data["token"]

    def begin_fresh_trip(self, token):
        status, dashboard = request("GET", "/api/v1/driver/dashboard", token=token)
        self.assertEqual(status, 200, dashboard)
        if dashboard["trip"]["status"] == "in_progress":
            self.assertEqual(request("POST", "/api/v1/driver/trip", {"action": "complete"}, token)[0], 200)
        status, started = request("POST", "/api/v1/driver/trip", {"action": "start"}, token)
        self.assertEqual(status, 200, started)
        self.assertEqual(started["status"], "in_progress")

    def test_01_health_and_existing_allocation_api(self):
        self.assertEqual(request("GET", "/api/v1/health"), (200, {"status": "ok"}))
        admin = self.login("admin", "admin@smartroute.local", "Admin@2026")
        status, overview = request("GET", "/api/v1/allocation/overview", token=admin)
        self.assertEqual(status, 200)
        self.assertEqual(overview["eligible_students"], 100)

    def test_02_login_rejects_bad_credentials_and_role(self):
        status, _ = request("POST", "/api/v1/auth/login", {"role": "driver", "username": "driver1@smartroute.local", "password": "incorrect"})
        self.assertEqual(status, 401)
        status, _ = request("POST", "/api/v1/auth/login", {"role": "admin", "username": "driver1@smartroute.local", "password": "Driver@2026"})
        self.assertEqual(status, 401)

    def test_03_demo_driver_directory_contains_every_driver(self):
        status, drivers = request("GET", "/api/v1/auth/demo-drivers")
        self.assertEqual(status, 200)
        self.assertEqual(len(drivers), 10)
        self.assertEqual(drivers[0]["username"], "driver1@smartroute.local")
        self.assertEqual(drivers[-1]["username"], "driver10@smartroute.local")

    def test_04_every_driver_can_login_and_only_sees_assigned_route(self):
        for number in range(1, 11):
            with self.subTest(driver=number):
                token = self.login("driver", f"driver{number}@smartroute.local", "Driver@2026")
                status, data = request("GET", "/api/v1/driver/dashboard", token=token)
                self.assertEqual(status, 200, data)
                self.assertEqual(data["driver"]["id"], f"DRV-{number:06}")
                self.assertEqual(data["route"]["id"], f"ROUTE-2026-{number:06}")
                self.assertEqual(data["bus"]["id"], f"BUS-{number:06}")

    def test_05_role_authorization_boundaries(self):
        driver = self.login("driver", "driver2@smartroute.local", "Driver@2026")
        parent = self.login("parent", "parent1@smartroute.local", "Parent@2026")
        admin = self.login("admin", "admin@smartroute.local", "Admin@2026")
        self.assertEqual(request("GET", "/api/v1/admin/operations", token=driver)[0], 403)
        self.assertEqual(request("GET", "/api/v1/driver/dashboard", token=parent)[0], 403)
        self.assertEqual(request("GET", "/api/v1/admin/operations", token=admin)[0], 200)
        self.assertEqual(request("GET", "/api/v1/allocation/assignments")[0], 401)
        self.assertEqual(request("GET", "/api/v1/analytics")[0], 401)
        self.assertEqual(request("GET", "/api/v1/allocation/assignments", token=driver)[0], 403)
        self.assertEqual(request("GET", "/api/v1/allocation/assignments", token=admin)[0], 200)
        self.assertEqual(request("POST", "/api/v1/allocation/run", {}, extra_headers={"X-Role": "admin"})[0], 401)
        self.assertEqual(request("POST", "/api/v1/allocation/run", {}, token=driver)[0], 403)

    def test_06_driver_admin_parent_flow_and_trip_restart(self):
        driver = self.login("driver", "driver1@smartroute.local", "Driver@2026")
        parent = self.login("parent", "parent1@smartroute.local", "Parent@2026")
        admin = self.login("admin", "admin@smartroute.local", "Admin@2026")

        self.begin_fresh_trip(driver)
        _, dashboard = request("GET", "/api/v1/driver/dashboard", token=driver)
        self.assertTrue(all(student["status"] == "waiting" for student in dashboard["students"]))

        status, _ = request("POST", "/api/v1/driver/location", {"latitude": 17.385, "longitude": 78.4867, "accuracy_meters": 12}, driver)
        self.assertEqual(status, 200)
        status, boarded = request("POST", "/api/v1/driver/student-event", {"student_id": "STU-000001", "event_type": "boarded"}, driver)
        self.assertEqual(status, 200, boarded)

        _, parent_view = request("GET", "/api/v1/parent/dashboard", token=parent)
        self.assertEqual(parent_view["student"]["name"], "Aarav Sharma")
        self.assertEqual(parent_view["status"], "boarded")
        self.assertEqual(parent_view["location"]["latitude"], 17.385)

        _, admin_view = request("GET", "/api/v1/admin/operations", token=admin)
        route = next(item for item in admin_view["routes"] if item["id"] == "ROUTE-2026-000001")
        self.assertEqual(route["trip_status"], "in_progress")
        self.assertEqual(route["students_on_bus"], 1)

        self.assertEqual(request("POST", "/api/v1/driver/trip", {"action": "complete"}, driver)[0], 200)
        self.assertEqual(request("POST", "/api/v1/driver/trip", {"action": "start"}, driver)[0], 200)
        _, new_run = request("GET", "/api/v1/driver/dashboard", token=driver)
        self.assertTrue(all(student["status"] == "waiting" for student in new_run["students"]))
        self.assertIsNone(new_run["location"])
        _, restarted_parent = request("GET", "/api/v1/parent/dashboard", token=parent)
        self.assertEqual(restarted_parent["status"], "trip_in_progress")
        self.assertEqual(restarted_parent["events"], [])
        self.assertIsNone(restarted_parent["location"])

    def test_07_logout_invalidates_session(self):
        token = self.login("driver", "driver3@smartroute.local", "Driver@2026")
        self.assertEqual(request("POST", "/api/v1/auth/logout", token=token)[0], 200)
        self.assertEqual(request("GET", "/api/v1/driver/dashboard", token=token)[0], 401)

    def test_08_pages_have_safe_brand_navigation(self):
        cases = [
            ("/", 'lang="en"', "allocation-table-wrap"),
            ("/login", 'href="/login"', "toggle-password"),
            ("/portal/driver", 'href="/portal/driver"', "route-map"),
            ("/portal/admin", 'href="/portal/admin"', "Route command board"),
            ("/portal/parent", 'href="/portal/parent"', "Journey timeline"),
        ]
        for path, brand_link, marker in cases:
            with self.subTest(path=path):
                status, page = request("GET", path)
                self.assertEqual(status, 200)
                self.assertIn(brand_link, page)
                self.assertIn(marker, page)

    def test_09_frontend_assets_are_available(self):
        assets = ("portal.js", "login.js", "driver.js", "admin.js", "parent.js", "portal.css", "login-access.css", "route-map.css")
        for asset in assets:
            with self.subTest(asset=asset):
                status, content = request("GET", f"/static/{asset}")
                self.assertEqual(status, 200)
                self.assertTrue(content.strip())

    def test_10_driver_trip_feedback_is_explicit(self):
        _, driver_js = request("GET", "/static/driver.js")
        _, portal_css = request("GET", "/static/portal.css")
        self.assertIn("Starting trip…", driver_js)
        self.assertIn("Trip started successfully", driver_js)
        self.assertIn("Trip started'", driver_js)
        self.assertIn("cursor:not-allowed", portal_css)
        self.assertIn(".is-loading{cursor:progress", portal_css)

    def test_11_student_event_transitions_and_onboard_count(self):
        driver = self.login("driver", "driver2@smartroute.local", "Driver@2026")
        admin = self.login("admin", "admin@smartroute.local", "Admin@2026")
        self.begin_fresh_trip(driver)
        _, dashboard = request("GET", "/api/v1/driver/dashboard", token=driver)
        student_id = dashboard["students"][0]["id"]

        self.assertEqual(request("POST", "/api/v1/driver/student-event", {"student_id": student_id, "event_type": "dropped_off"}, driver)[0], 409)
        self.assertEqual(request("POST", "/api/v1/driver/student-event", {"student_id": student_id, "event_type": "boarded"}, driver)[0], 200)
        self.assertEqual(request("POST", "/api/v1/driver/student-event", {"student_id": student_id, "event_type": "boarded"}, driver)[0], 409)
        _, active_admin = request("GET", "/api/v1/admin/operations", token=admin)
        route = next(item for item in active_admin["routes"] if item["id"] == dashboard["route"]["id"])
        self.assertEqual(route["students_on_bus"], 1)

        self.assertEqual(request("POST", "/api/v1/driver/student-event", {"student_id": student_id, "event_type": "dropped_off"}, driver)[0], 200)
        self.assertEqual(request("POST", "/api/v1/driver/student-event", {"student_id": student_id, "event_type": "boarded"}, driver)[0], 409)
        _, completed_admin = request("GET", "/api/v1/admin/operations", token=admin)
        route = next(item for item in completed_admin["routes"] if item["id"] == dashboard["route"]["id"])
        self.assertEqual(route["students_on_bus"], 0)

    def test_12_repeated_manual_assignment_uses_unique_ids(self):
        admin = self.login("admin", "admin@smartroute.local", "Admin@2026")
        payload = {
            "student_id": "STU-000001",
            "route_id": "ROUTE-2026-000001",
            "stop_id": "STOP-000001",
            "effective_from": "2026-11-14",
        }
        first_status, first = request("POST", "/api/v1/allocation/manual", payload, admin)
        second_status, second = request("POST", "/api/v1/allocation/manual", payload, admin)
        self.assertEqual(first_status, 200, first)
        self.assertEqual(second_status, 200, second)
        self.assertNotEqual(first["assignment_id"], second["assignment_id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
