from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import unittest

from playwright.sync_api import Error as PlaywrightError, sync_playwright


class _QuietStaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


class SiteBrowserTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        repository_root = Path(__file__).resolve().parents[1]
        handler = partial(
            _QuietStaticHandler,
            directory=str(repository_root / "docs"),
        )
        cls.http_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.server_thread = Thread(
            target=cls.http_server.serve_forever,
            daemon=True,
        )
        cls.server_thread.start()
        host, port = cls.http_server.server_address
        cls.base_url = f"http://{host}:{port}"

        cls.playwright = sync_playwright().start()
        try:
            cls.browser = cls.playwright.chromium.launch(headless=True)
        except PlaywrightError as error:
            if "Executable doesn't exist" not in str(error):
                raise
            cls.browser = cls.playwright.chromium.launch(
                channel="chrome",
                headless=True,
            )

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.http_server.shutdown()
        cls.http_server.server_close()
        cls.server_thread.join()
        super().tearDownClass()

    def tearDown(self):
        if hasattr(self, "browser_context"):
            self.browser_context.close()
        super().tearDown()

    def open_page(
        self,
        path="/",
        *,
        width=1280,
        height=720,
        reduced_motion="no-preference",
    ):
        self.browser_context = self.browser.new_context(
            viewport={"width": width, "height": height},
            reduced_motion=reduced_motion,
        )
        page = self.browser_context.new_page()
        response = page.goto(f"{self.base_url}{path}", wait_until="networkidle")
        self.assertIsNotNone(response)
        self.assertEqual(
            response.status,
            200,
            f"Expected the static site at {path}, got HTTP {response.status}",
        )
        return page
