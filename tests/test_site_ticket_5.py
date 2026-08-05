from urllib.parse import urlparse

from playwright.sync_api import expect

from tests.site_test_support import SiteBrowserTestCase


class Ticket5AcceptanceTests(SiteBrowserTestCase):
    CANONICAL_URL = "https://nuts-and-bytes.github.io/zero-to-one-product/"
    PAGE_TITLE = "Zero-to-One Product｜从模糊想法到首个可用版本"
    DESCRIPTION = (
        "Zero-to-One Product 把 Matt Pocock Skills 的产品发现与 Superpowers "
        "的工程交付组合成一条固定、可恢复、有安全门的 0→1 产品路线。"
    )
    SHARE_IMAGE_URL = CANONICAL_URL + "assets/share-card.png"
    MATT_SKILLS = {
        "grill-me",
        "grill-with-docs",
        "wayfinder",
        "research",
        "prototype",
        "to-spec",
        "to-tickets",
        "diagnosing-bugs",
        "code-review",
        "handoff",
    }
    SUPERPOWERS_SKILLS = {
        "using-git-worktrees",
        "writing-plans",
        "test-driven-development",
        "systematic-debugging",
        "requesting-code-review",
        "verification-before-completion",
        "finishing-a-development-branch",
    }
    COMMANDS = [
        "npx skills@latest add mattpocock/skills",
        "/plugins",
        "codex plugin marketplace add nuts-and-bytes/zero-to-one-product",
        "codex plugin add zero-to-one-product@zero-to-one-product",
        "codex plugin marketplace upgrade zero-to-one-product",
        "$zero-to-one-product <你的产品想法或当前 0→1 目标>",
    ]

    def _required_section(self, page, section_id):
        section = page.locator(f"#{section_id}")
        self.assertEqual(section.count(), 1, f"Missing #{section_id} section")
        return section

    def test_dependency_map_exposes_the_two_exact_upstream_sets(self):
        page = self.open_page(reduced_motion="reduce")
        dependencies = self._required_section(page, "dependencies")

        expected_groups = {
            "matt": self.MATT_SKILLS,
            "superpowers": self.SUPERPOWERS_SKILLS,
        }
        for owner, expected_skills in expected_groups.items():
            with self.subTest(owner=owner):
                group = dependencies.locator(
                    f"[data-dependency-owner='{owner}']"
                )
                self.assertEqual(
                    group.count(),
                    1,
                    f"Missing dependency group for {owner}",
                )
                skill_contracts = group.locator("[data-skill]").evaluate_all(
                    """
                    elements => elements.map(element => ({
                      name: element.dataset.skill,
                      text: element.textContent.trim().replace(/\\s+/g, " "),
                    }))
                    """
                )
                self.assertEqual(
                    {item["name"] for item in skill_contracts},
                    expected_skills,
                )
                self.assertEqual(len(skill_contracts), len(expected_skills))
                for item in skill_contracts:
                    self.assertEqual(item["text"], item["name"])

        dependency_text = " ".join(dependencies.inner_text().split())
        self.assertRegex(
            dependency_text,
            r"路由器.*不.*捆绑.*Matt.*也不.*捆绑.*Superpowers",
        )

        source_urls = set(
            dependencies.locator("a[href]").evaluate_all(
                "elements => elements.map(element => element.href)"
            )
        )
        self.assertTrue(
            {
                "https://github.com/mattpocock/skills",
                "https://github.com/obra/superpowers",
            }.issubset(source_urls)
        )

    def test_install_flow_has_exact_order_commands_and_stop_rules(self):
        page = self.open_page(reduced_motion="reduce")
        install = self._required_section(page, "install")

        phases = install.locator("[data-install-phase]").evaluate_all(
            """
            elements => elements.map(element => ({
              phase: element.dataset.installPhase,
              text: element.textContent.trim().replace(/\\s+/g, " "),
            }))
            """
        )
        self.assertEqual(
            [item["phase"] for item in phases],
            [
                "matt",
                "superpowers",
                "router",
                "update",
                "use",
                "troubleshooting",
            ],
        )

        phase_text = {item["phase"]: item["text"] for item in phases}
        for owner, label in (
            ("matt", "Matt Pocock Skills"),
            ("superpowers", "Superpowers"),
            ("router", "Zero-to-One Product"),
        ):
            self.assertIn(label, phase_text[owner])

        readable_commands = install.locator("code[data-command]").evaluate_all(
            "elements => elements.map(element => "
            "element.textContent.trim().replace(/\\s+/g, ' '))"
        )
        self.assertEqual(readable_commands, self.COMMANDS)

        install_text = " ".join(install.inner_text().split())
        for pattern in (
            r"Matt.*Superpowers.*Zero-to-One Product",
            r"Matt.*Superpowers.*分别.*上游.*更新",
            r"安装.*更新.*新建.*Codex 对话",
            r"显式调用.*优先|优先.*显式调用",
            r"依赖.*缺失.*歧义.*停止",
            r"报告.*精确.*Skill 名称",
            r"不.*猜测.*机器.*路径",
        ):
            self.assertRegex(install_text, pattern)

        source_urls = set(
            install.locator("a[href]").evaluate_all(
                "elements => elements.map(element => element.href)"
            )
        )
        self.assertTrue(
            {
                "https://github.com/mattpocock/skills",
                "https://github.com/obra/superpowers",
                "https://github.com/nuts-and-bytes/zero-to-one-product",
            }.issubset(source_urls)
        )

    def test_every_command_copies_by_pointer_and_keyboard_with_feedback(self):
        page = self.open_page(reduced_motion="reduce")
        install = self._required_section(page, "install")
        self.browser_context.grant_permissions(
            ["clipboard-read", "clipboard-write"],
            origin=self.base_url,
        )

        controls = install.locator("[data-copy-command]")
        self.assertEqual(controls.count(), len(self.COMMANDS))
        self.assertEqual(
            controls.evaluate_all(
                "elements => elements.map(element => "
                "element.dataset.copyCommand)"
            ),
            self.COMMANDS,
        )

        for index, expected_command in enumerate(self.COMMANDS):
            with self.subTest(command=expected_command):
                control = controls.nth(index)
                block = control.locator("xpath=ancestor::*[@data-command-block][1]")
                self.assertEqual(
                    block.count(),
                    1,
                    "Copy control must be bound to a readable command block",
                )
                readable_command = block.locator("code[data-command]")
                self.assertEqual(readable_command.count(), 1)
                self.assertEqual(
                    readable_command.inner_text().strip(),
                    expected_command,
                )
                status = block.locator("[data-copy-status][aria-live]")
                self.assertEqual(status.count(), 1)
                self.assertEqual(status.get_attribute("aria-live"), "polite")

                control.click()
                expect(status).to_contain_text("已复制", timeout=700)
                expect(status).to_be_visible(timeout=700)
                self.assertEqual(
                    page.evaluate("navigator.clipboard.readText()"),
                    expected_command,
                )

                page.evaluate("navigator.clipboard.writeText('')")
                control.focus()
                page.keyboard.press("Enter")
                expect(status).to_contain_text("已复制", timeout=700)
                self.assertEqual(
                    page.evaluate("navigator.clipboard.readText()"),
                    expected_command,
                )

    def test_commands_remain_readable_and_selectable_without_javascript(self):
        page = self.open_page(
            reduced_motion="reduce",
            java_script_enabled=False,
        )
        install = self._required_section(page, "install")
        command_contracts = install.locator("code[data-command]").evaluate_all(
            """
            elements => elements.map(element => {
              const style = getComputedStyle(element);
              const rect = element.getBoundingClientRect();
              return {
                text: element.textContent.trim().replace(/\\s+/g, " "),
                visible: element.checkVisibility({
                  checkOpacity: true,
                  checkVisibilityCSS: true,
                }),
                width: rect.width,
                height: rect.height,
                userSelect: style.userSelect,
              };
            })
            """
        )
        self.assertEqual(
            [item["text"] for item in command_contracts],
            self.COMMANDS,
        )
        for item in command_contracts:
            self.assertTrue(item["visible"])
            self.assertGreater(item["width"], 0)
            self.assertGreater(item["height"], 0)
            self.assertNotEqual(item["userSelect"], "none")

    def test_release_metadata_share_image_and_pages_files_are_http_ready(self):
        page = self.open_page(reduced_motion="reduce")

        self.assertEqual(page.title(), self.PAGE_TITLE)
        description = page.locator("meta[name='description']")
        self.assertEqual(description.count(), 1)
        self.assertEqual(description.get_attribute("content"), self.DESCRIPTION)
        canonical = page.locator("link[rel='canonical']")
        self.assertEqual(canonical.count(), 1)
        self.assertEqual(canonical.get_attribute("href"), self.CANONICAL_URL)

        expected_metadata = {
            "meta[property='og:title']": self.PAGE_TITLE,
            "meta[property='og:description']": self.DESCRIPTION,
            "meta[property='og:type']": "website",
            "meta[property='og:url']": self.CANONICAL_URL,
            "meta[property='og:image']": self.SHARE_IMAGE_URL,
            "meta[property='og:locale']": "zh_CN",
            "meta[name='twitter:card']": "summary_large_image",
            "meta[name='twitter:title']": self.PAGE_TITLE,
            "meta[name='twitter:description']": self.DESCRIPTION,
            "meta[name='twitter:image']": self.SHARE_IMAGE_URL,
        }
        for selector, expected_content in expected_metadata.items():
            with self.subTest(selector=selector):
                metadata = page.locator(selector)
                self.assertEqual(metadata.count(), 1, f"Missing {selector}")
                self.assertEqual(
                    metadata.get_attribute("content"),
                    expected_content,
                )

        share_path = urlparse(self.SHARE_IMAGE_URL).path.replace(
            "/zero-to-one-product", ""
        )
        share_response = page.request.get(f"{self.base_url}{share_path}")
        self.assertEqual(share_response.status, 200)
        self.assertEqual(
            share_response.headers.get("content-type"),
            "image/png",
        )
        share_dimensions = page.evaluate(
            """
            async url => {
              const image = new Image();
              const loaded = new Promise((resolve, reject) => {
                image.addEventListener("load", resolve, {once: true});
                image.addEventListener("error", reject, {once: true});
              });
              image.src = url;
              await loaded;
              return [image.naturalWidth, image.naturalHeight];
            }
            """,
            f"{self.base_url}{share_path}",
        )
        self.assertEqual(share_dimensions, [1200, 630])

        robots_response = page.request.get(f"{self.base_url}/robots.txt")
        self.assertEqual(robots_response.status, 200)
        robots_text = robots_response.text()
        self.assertRegex(robots_text, r"(?im)^User-agent:\s*\*$")
        self.assertRegex(robots_text, r"(?im)^Allow:\s*/$")
        self.assertIn(
            f"Sitemap: {self.CANONICAL_URL}sitemap.xml",
            robots_text,
        )

        sitemap_response = page.request.get(f"{self.base_url}/sitemap.xml")
        self.assertEqual(sitemap_response.status, 200)
        self.assertIn(f"<loc>{self.CANONICAL_URL}</loc>", sitemap_response.text())

        nojekyll_response = page.request.get(f"{self.base_url}/.nojekyll")
        self.assertEqual(nojekyll_response.status, 200)

    def test_release_navigation_focus_and_content_hygiene_are_accessible(self):
        page = self.open_page(reduced_motion="reduce")

        self.assertEqual(page.locator("h1").count(), 1)
        self.assertEqual(
            page.locator(
                "a[href^='#']"
            ).evaluate_all(
                """
                elements => elements.filter(element => {
                  const href = element.getAttribute("href");
                  if (!href || href === "#") {
                    return true;
                  }
                  return !document.getElementById(
                    decodeURIComponent(href.slice(1))
                  );
                }).map(element => element.getAttribute("href"))
                """
            ),
            [],
        )
        self.assertEqual(
            page.locator("#primary-navigation a").evaluate_all(
                "elements => elements.map(element => "
                "element.getAttribute('href'))"
            ),
            [
                "#value",
                "#classifier",
                "#workflow",
                "#ownership",
                "#dependencies",
                "#install",
                "https://github.com/nuts-and-bytes/zero-to-one-product",
            ],
        )

        focusable_count = page.evaluate(
            """
            () => {
              const selector = [
                "a[href]",
                "button:not([disabled])",
                "[tabindex]:not([tabindex='-1'])",
              ].join(",");
              const elements = Array.from(document.querySelectorAll(selector))
                .filter(element => {
                  const style = getComputedStyle(element);
                  const rect = element.getBoundingClientRect();
                  return style.display !== "none"
                    && style.visibility !== "hidden"
                    && rect.width > 0
                    && rect.height > 0;
                });
              elements.forEach((element, index) => {
                element.dataset.acceptanceFocusOrder = String(index);
              });
              return elements.length;
            }
            """
        )
        self.assertGreater(focusable_count, 0)
        for expected_index in range(focusable_count):
            page.keyboard.press("Tab")
            focus_contract = page.evaluate(
                """
                () => {
                  const element = document.activeElement;
                  const style = getComputedStyle(element);
                  return {
                    order: Number(element.dataset.acceptanceFocusOrder),
                    outlineStyle: style.outlineStyle,
                    outlineWidth: Number.parseFloat(style.outlineWidth),
                    boxShadow: style.boxShadow,
                  };
                }
                """
            )
            self.assertEqual(focus_contract["order"], expected_index)
            self.assertTrue(
                (
                    focus_contract["outlineStyle"] != "none"
                    and focus_contract["outlineWidth"] > 0
                )
                or focus_contract["boxShadow"] != "none",
                f"Missing visible focus indicator at tab stop {expected_index}",
            )

        html = page.locator("html").inner_text()
        source = page.content()
        for forbidden in (
            "/Users/",
            "file://",
            "C:\\Users\\",
            "TODO",
            "TBD",
            "Lorem ipsum",
            "placeholder",
            "data-variant",
            "variant-prev",
            "variant-next",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, html + source)

        external_urls = set(
            page.locator("a[href^='https://']").evaluate_all(
                "elements => elements.map(element => element.href)"
            )
        )
        self.assertTrue(
            {
                "https://github.com/mattpocock/skills",
                "https://github.com/obra/superpowers",
                "https://github.com/nuts-and-bytes/zero-to-one-product",
            }.issubset(external_urls)
        )

    def test_full_release_survives_responsive_and_failed_image_conditions(self):
        release_sections = (
            "value",
            "classifier",
            "workflow",
            "ownership",
            "guardrails",
            "dependencies",
            "install",
            "scope-transfer",
        )
        for width, height in ((1280, 720), (390, 844)):
            with self.subTest(viewport=(width, height)):
                page = self.open_page(
                    width=width,
                    height=height,
                    reduced_motion="reduce",
                )
                try:
                    scroll_width, client_width = page.evaluate(
                        "[document.documentElement.scrollWidth, "
                        "document.documentElement.clientWidth]"
                    )
                    self.assertLessEqual(scroll_width, client_width)
                    for section_id in release_sections:
                        section = self._required_section(page, section_id)
                        section.scroll_into_view_if_needed(timeout=700)
                        contract = section.evaluate(
                            """
                            element => {
                              const rect = element.getBoundingClientRect();
                              return {
                                visible: element.checkVisibility({
                                  checkOpacity: true,
                                  checkVisibilityCSS: true,
                                }),
                                width: rect.width,
                                height: rect.height,
                                heading: element.querySelector("h2")
                                  ?.textContent.trim() ?? "",
                              };
                            }
                            """
                        )
                        self.assertTrue(contract["visible"])
                        self.assertGreater(contract["width"], 0)
                        self.assertGreater(contract["height"], 0)
                        self.assertTrue(contract["heading"])
                finally:
                    self.browser_context.close()
                    del self.browser_context

        console_errors = []
        page_errors = []
        failed_requests = []
        intentionally_aborted = set()
        self.browser_context = self.browser.new_context(
            viewport={"width": 390, "height": 844},
            reduced_motion="reduce",
        )
        page = self.browser_context.new_page()
        page.on(
            "console",
            lambda message: console_errors.append(
                (message.text, message.location.get("url", ""))
            )
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(
                (request.url, request.failure)
            ),
        )

        def abort_images(route, request):
            if request.resource_type == "image":
                intentionally_aborted.add(request.url)
                route.abort("failed")
            else:
                route.continue_()

        page.route("**/*", abort_images)
        response = page.goto(
            f"{self.base_url}/",
            wait_until="domcontentloaded",
            timeout=5_000,
        )
        self.assertIsNotNone(response)
        self.assertEqual(response.status, 200)
        page.wait_for_timeout(250)

        for selector, required_text in (
            (".hero-copy", "有状态路由器"),
            ("#value", "控制权"),
            ("#install", "$zero-to-one-product"),
        ):
            with self.subTest(resilient_selector=selector):
                content = page.locator(selector)
                self.assertEqual(content.count(), 1)
                expect(content).to_be_visible(timeout=700)
                self.assertIn(required_text, content.inner_text())

        unexpected_console_errors = [
            (message, url)
            for message, url in console_errors
            if not (
                url in intentionally_aborted
                and "Failed to load resource" in message
                and "ERR_FAILED" in message
            )
        ]
        self.assertEqual(unexpected_console_errors, [])
        self.assertEqual(page_errors, [])
        self.assertGreater(len(intentionally_aborted), 0)
        self.assertEqual(
            {url for url, _failure in failed_requests},
            intentionally_aborted,
        )
        for failed_url, failure in failed_requests:
            self.assertIn(failed_url, intentionally_aborted)
            self.assertRegex(failure or "", r"ERR_FAILED|aborted|failed")


if __name__ == "__main__":
    import unittest

    unittest.main()
