import json
import re
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from lead_review.ui import make_server

class LocalDemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = make_server(self.tmp.name, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def get(self, path):
        with urlopen(self.url + path) as r:
            return r.read()

    def post(self, op, token=True, origin=True):
        headers = {"Content-Type": "application/json"}
        if token: headers["X-Demo-Token"] = self.server.demo.token
        if origin: headers["Origin"] = self.url
        request = Request(self.url + "/action", json.dumps({"op": op}).encode(), headers)
        with urlopen(request) as r:
            return json.load(r)

    def test_demo_workflow_and_missing_link_control(self):
        html = self.get("/").decode()
        self.assertNotIn("__DEMO_TOKEN__", html)
        self.assertIn(self.server.demo.token, html)
        initial = json.loads(self.get("/state"))
        corrected = self.post("correct")
        self.assertEqual(len(corrected["review_requests"]), 1)
        metadata = self.post("metadata")
        self.assertEqual(len(metadata["review_requests"]), 1)
        reviewed = self.post("review")
        self.assertEqual(len(reviewed["human_reviews"]), 1)
        self.assertEqual(reviewed["nodes"][3], initial["nodes"][3])
        self.assertEqual(json.loads(self.get("/export")), reviewed)
        old_path = self.server.demo.path
        missing = self.post("missing_links")
        self.assertTrue(old_path.exists())
        self.assertEqual(missing["coverage"]["status"], "incomplete")
        self.assertEqual(self.post("correct")["review_requests"], [])

    def test_cross_origin_or_missing_token_cannot_mutate(self):
        initial = self.get("/state")
        for token, origin in ((False, True), (True, False), (False, False)):
            with self.subTest(token=token, origin=origin), self.assertRaises(HTTPError) as context:
                self.post("correct", token, origin)
            self.assertEqual(context.exception.code, 403)
        self.assertEqual(self.get("/state"), initial)

if __name__ == "__main__":
    unittest.main()
