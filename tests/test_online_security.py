import base64
import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from chugchug.server import Handler, main


class PrivateDemoHandler(Handler):
    online_mode = True
    access_username = "reviewer"
    access_password = "not-a-real-password-that-is-long-enough"
    public_origin = "https://review.example.test"


class OnlineAccessTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), PrivateDemoHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:%d" % self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, method="GET", headers=None, body=None):
        request = urllib.request.Request(self.base + path, data=body, headers=headers or {}, method=method)
        try:
            response = urllib.request.urlopen(request, timeout=2)
            return response.status, response.headers, response.read()
        except urllib.error.HTTPError as response:
            return response.code, response.headers, response.read()

    def auth_header(self, username="reviewer", password="not-a-real-password-that-is-long-enough"):
        token = base64.b64encode((username + ":" + password).encode()).decode()
        return {"Authorization": "Basic " + token}

    def test_api_requires_configured_credentials(self):
        status, headers, body = self.request("/api/queue")
        self.assertEqual(status, 401)
        self.assertIn("Basic", headers["WWW-Authenticate"])
        self.assertEqual(body, b"Authentication required\n")

    def test_wrong_password_is_rejected(self):
        status, _, _ = self.request("/api/queue", headers=self.auth_header(password="wrong"))
        self.assertEqual(status, 401)

    def test_cross_origin_writes_are_rejected(self):
        headers = {**self.auth_header(), "Origin": "https://outside.example.test", "Content-Type": "application/json"}
        status, _, body = self.request("/api/unknown", "POST", headers, json.dumps({}).encode())
        self.assertEqual(status, 403)
        self.assertIn(b"origin", body.lower())

    def test_same_origin_write_passes_access_checks(self):
        headers = {**self.auth_header(), "Origin": PrivateDemoHandler.public_origin, "Content-Type": "application/json"}
        status, _, _ = self.request("/api/unknown", "POST", headers, json.dumps({}).encode())
        self.assertEqual(status, 404)

    def test_health_probe_returns_no_application_data_without_auth(self):
        status, _, body = self.request("/healthz")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"ok\n")

    def test_online_startup_fails_without_access_configuration(self):
        with patch.dict(os.environ, {"CHUGCHUG_ONLINE": "1"}, clear=True), patch.object(sys, "argv", ["chugchug.server"]):
            with self.assertRaises(SystemExit) as result:
                main()
        self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
