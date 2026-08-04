from contextlib import ExitStack
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
        cls.class_stack = ExitStack()
        try:
            repository_root = Path(__file__).resolve().parents[1]
            handler = partial(
                _QuietStaticHandler,
                directory=str(repository_root / "docs"),
            )
            cls.http_server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            cls.class_stack.callback(cls.http_server.server_close)

            cls.server_thread = Thread(
                target=cls.http_server.serve_forever,
                daemon=True,
            )
            cls.server_thread.start()
            cls.class_stack.callback(cls.server_thread.join)
            cls.class_stack.callback(cls.http_server.shutdown)
            host, port = cls.http_server.server_address
            cls.base_url = f"http://{host}:{port}"

            cls.playwright = sync_playwright().start()
            cls.class_stack.callback(cls.playwright.stop)
            try:
                cls.browser = cls.playwright.chromium.launch(headless=True)
            except PlaywrightError as bundled_error:
                if "Executable doesn't exist" not in str(bundled_error):
                    raise
                try:
                    cls.browser = cls.playwright.chromium.launch(
                        channel="chrome",
                        headless=True,
                    )
                except PlaywrightError as fallback_error:
                    raise RuntimeError(
                        "Bundled Chromium is not installed and the local "
                        "Chrome fallback could not start. Run "
                        "`python3 -m playwright install chromium`."
                    ) from fallback_error
            cls.class_stack.callback(cls.browser.close)
        except BaseException:
            cls.class_stack.close()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            cls.class_stack.close()
        finally:
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
        java_script_enabled=True,
    ):
        self.browser_context = self.browser.new_context(
            viewport={"width": width, "height": height},
            reduced_motion=reduced_motion,
            java_script_enabled=java_script_enabled,
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
