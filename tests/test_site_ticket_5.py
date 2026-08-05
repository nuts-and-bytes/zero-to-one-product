from base64 import b64decode
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread
from time import monotonic
from urllib.parse import urlparse
from xml.etree import ElementTree

from playwright.sync_api import expect

from tests.site_test_support import SiteBrowserTestCase


class _HangingImageHandler(BaseHTTPRequestHandler):
    request_started = Event()
    release_response = Event()
    response_finished = Event()
    image_bytes = b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        "+M/wHwAF/gL+X3v5WQAAAABJRU5ErkJggg=="
    )

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(self.image_bytes)))
        self.end_headers()
        self.request_started.set()
        self.release_response.wait(timeout=4)
        self.wfile.write(self.image_bytes)
        self.response_finished.set()

    def log_message(self, format, *args):
        pass


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
    INSTALL_RULES = {
        "安装或更新后必须新建一个 Codex 对话",
        "显式调用 $zero-to-one-product 比隐式触发更可靠",
        "依赖缺失或存在歧义时必须停止",
        "必须报告精确的 Skill 名称",
        "禁止猜测机器相关路径",
    }

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
                "troubleshoot",
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

        install_rules = {
            " ".join(text.split())
            for text in install.locator("[data-install-rule]").all_text_contents()
        }
        self.assertEqual(install_rules, self.INSTALL_RULES)

        install_text = " ".join(install.inner_text().split())
        self.assertRegex(install_text, r"Matt.*Superpowers.*Zero-to-One Product")
        self.assertRegex(install_text, r"Matt.*Superpowers.*分别.*上游.*更新")
        for rejected_meaning in (
            "无需新建 Codex 对话",
            "不要新建 Codex 对话",
            "不必新建 Codex 对话",
            "依赖缺失或存在歧义时不停止",
            "无需停止",
            "报告不精确的 Skill 名称",
            "可以猜测机器路径",
            "允许猜测机器路径",
            "猜测路径即可",
        ):
            self.assertNotIn(rejected_meaning, install_text)

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

        controls = install.locator(
            "button[type='button'][data-copy-command]"
        )
        self.assertEqual(controls.count(), len(self.COMMANDS))
        self.assertEqual(
            install.locator("[data-copy-command]").count(),
            len(self.COMMANDS),
            "Every copy control must be a native type=button element",
        )
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
                accessible_name = control.evaluate(
                    """
                    element => {
                      const labelledBy = element.getAttribute("aria-labelledby");
                      if (labelledBy) {
                        return labelledBy.split(/\\s+/)
                          .map(id => document.getElementById(id)?.textContent ?? "")
                          .join(" ").trim();
                      }
                      return (element.getAttribute("aria-label")
                        || element.textContent).trim();
                    }
                    """
                )
                self.assertTrue(accessible_name)
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

        page.reload(wait_until="networkidle")
        controls = page.locator(
            "#install button[type='button'][data-copy-command]"
        )
        reached_commands = []
        maximum_tab_stops = page.locator(
            "a[href], button:not([disabled]), "
            "[tabindex]:not([tabindex='-1'])"
        ).count() + 2
        for _tab_stop in range(maximum_tab_stops):
            page.keyboard.press("Tab")
            active_command = page.evaluate(
                "document.activeElement?.dataset.copyCommand ?? null"
            )
            if active_command is None:
                continue
            self.assertEqual(
                page.evaluate("document.activeElement.tagName"),
                "BUTTON",
            )
            reached_commands.append(active_command)
            active_control = controls.nth(len(reached_commands) - 1)
            self.assertTrue(active_control.evaluate("el => el === document.activeElement"))
            status = active_control.locator(
                "xpath=ancestor::*[@data-command-block][1]"
            ).locator("[data-copy-status][aria-live]")

            for key in ("Enter", "Space"):
                page.evaluate("navigator.clipboard.writeText('')")
                page.keyboard.press(key)
                expect(status).to_contain_text("已复制", timeout=700)
                expect(status).to_be_visible(timeout=700)
                self.assertEqual(
                    page.evaluate("navigator.clipboard.readText()"),
                    active_command,
                )
            if len(reached_commands) == len(self.COMMANDS):
                break
        self.assertEqual(reached_commands, self.COMMANDS)

        page.reload(wait_until="networkidle")
        page.evaluate("navigator.clipboard.writeText('sentinel')")
        page.evaluate(
            """
            () => {
              Object.defineProperty(navigator.clipboard, "writeText", {
                configurable: true,
                value: () => Promise.reject(
                  new DOMException("clipboard denied", "NotAllowedError")
                ),
              });
              document.execCommand = () => false;
            }
            """
        )
        rejected_control = page.locator(
            "#install button[type='button'][data-copy-command]"
        ).first
        rejected_status = rejected_control.locator(
            "xpath=ancestor::*[@data-command-block][1]"
        ).locator("[data-copy-status][aria-live]")
        rejected_control.click()
        expect(rejected_status).to_contain_text("复制失败", timeout=700)
        expect(rejected_status).to_be_visible(timeout=700)
        self.assertNotIn("已复制", rejected_status.inner_text())
        self.assertEqual(
            page.evaluate("navigator.clipboard.readText()"),
            "sentinel",
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
        robots_lines = [
            line.strip()
            for line in robots_response.text().splitlines()
            if line.strip()
        ]
        self.assertEqual(
            robots_lines,
            [
                "User-agent: *",
                "Allow: /",
                f"Sitemap: {self.CANONICAL_URL}sitemap.xml",
            ],
        )

        sitemap_response = page.request.get(f"{self.base_url}/sitemap.xml")
        self.assertEqual(sitemap_response.status, 200)
        sitemap_root = ElementTree.fromstring(sitemap_response.body())
        sitemap_locations = [
            (location.text or "").strip()
            for location in sitemap_root.findall(".//{*}loc")
        ]
        self.assertEqual(sitemap_locations, [self.CANONICAL_URL])

        nojekyll_response = page.request.get(f"{self.base_url}/.nojekyll")
        self.assertEqual(nojekyll_response.status, 200)
        self.assertEqual(len(nojekyll_response.body()), 0)

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

        heading_contract = page.locator("h1, h2, h3, h4, h5, h6").evaluate_all(
            """
            elements => elements.map(element => ({
              level: Number(element.tagName.slice(1)),
              id: element.id,
              text: element.textContent.trim().replace(/\\s+/g, " "),
            }))
            """
        )
        self.assertTrue(all(item["text"] for item in heading_contract))
        self.assertEqual(
            sum(item["level"] == 1 for item in heading_contract),
            1,
        )
        for previous, current in zip(heading_contract, heading_contract[1:]):
            self.assertLessEqual(
                current["level"],
                previous["level"] + 1,
                f"Heading level jumps from {previous} to {current}",
            )
        heading_ids = [item["id"] for item in heading_contract if item["id"]]
        self.assertEqual(len(heading_ids), len(set(heading_ids)))
        self.assertEqual(
            page.locator("[id]").evaluate_all(
                """
                elements => {
                  const ids = elements.map(element => element.id);
                  return ids.filter((id, index) => ids.indexOf(id) !== index);
                }
                """
            ),
            [],
        )
        labelled_sections = page.locator("section[aria-labelledby]")
        self.assertGreater(labelled_sections.count(), 0)
        for section_index in range(labelled_sections.count()):
            section = labelled_sections.nth(section_index)
            relationship = section.evaluate(
                """
                element => {
                  const ids = element.getAttribute("aria-labelledby")
                    .trim().split(/\\s+/);
                  const labels = ids.map(id => document.getElementById(id));
                  return {
                    ids,
                    allExist: labels.every(Boolean),
                    allHeadings: labels.every(label =>
                      /^H[1-6]$/.test(label?.tagName ?? "")
                    ),
                    allContained: labels.every(label => element.contains(label)),
                  };
                }
                """
            )
            self.assertEqual(
                len(relationship["ids"]),
                len(set(relationship["ids"])),
            )
            self.assertTrue(relationship["allExist"])
            self.assertTrue(relationship["allHeadings"])
            self.assertTrue(relationship["allContained"])

        internal_navigation = page.locator(
            "#primary-navigation a[href^='#']"
        )
        self.assertEqual(internal_navigation.count(), 6)
        for link_index in range(internal_navigation.count()):
            link = internal_navigation.nth(link_index)
            href = link.get_attribute("href")
            link.click()
            page.wait_for_function(
                "expectedHash => location.hash === expectedHash",
                arg=href,
                timeout=700,
            )
            target_contract = page.locator(href).evaluate(
                """
                (target, link) => {
                  const rect = target.getBoundingClientRect();
                  const active = document.activeElement;
                  return {
                    intersectsViewport:
                      rect.bottom > 0 && rect.top < window.innerHeight,
                    focusIsReasonable:
                      active === link
                      || active === target
                      || target.contains(active),
                  };
                }
                """,
                link.element_handle(),
            )
            self.assertTrue(target_contract["intersectsViewport"])
            self.assertTrue(target_contract["focusIsReasonable"])

        page.evaluate("document.activeElement?.blur()")
        page.goto(f"{self.base_url}/", wait_until="networkidle")
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
                    if width == 390:
                        narrow_content = page.locator(
                            "#dependencies [data-skill], "
                            "#install code[data-command]"
                        )
                        self.assertEqual(narrow_content.count(), 23)
                        narrow_contracts = narrow_content.evaluate_all(
                            """
                            elements => elements.map(element => {
                              const rect = element.getBoundingClientRect();
                              return {
                                text: element.textContent.trim(),
                                visible: element.checkVisibility({
                                  checkOpacity: true,
                                  checkVisibilityCSS: true,
                                }),
                                left: rect.left,
                                right: rect.right,
                                clientWidth: element.clientWidth,
                                scrollWidth: element.scrollWidth,
                                documentWidth:
                                  document.documentElement.clientWidth,
                              };
                            })
                            """
                        )
                        for item in narrow_contracts:
                            self.assertTrue(item["text"])
                            self.assertTrue(item["visible"])
                            self.assertGreaterEqual(item["left"], 0)
                            self.assertLessEqual(
                                item["right"], item["documentWidth"] + 0.5
                            )
                            self.assertLessEqual(
                                item["scrollWidth"], item["clientWidth"] + 1
                            )
                        scroll_width, client_width = page.evaluate(
                            "[document.documentElement.scrollWidth, "
                            "document.documentElement.clientWidth]"
                        )
                        self.assertEqual(scroll_width, client_width)
                finally:
                    self.browser_context.close()
                    del self.browser_context

        _HangingImageHandler.request_started = Event()
        _HangingImageHandler.release_response = Event()
        _HangingImageHandler.response_finished = Event()
        hanging_server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            _HangingImageHandler,
        )
        hanging_thread = Thread(
            target=hanging_server.serve_forever,
            daemon=True,
        )
        hanging_thread.start()
        slow_host, slow_port = hanging_server.server_address
        slow_image_url = f"http://{slow_host}:{slow_port}/slow.png"

        console_errors = []
        page_errors = []
        failed_requests = []
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
            lambda request: failed_requests.append((request.url, request.failure)),
        )

        def delay_images(route, request):
            if request.resource_type == "image":
                route.continue_(url=slow_image_url)
            else:
                route.continue_()

        page.route("**/*", delay_images)
        try:
            response = page.goto(
                f"{self.base_url}/",
                wait_until="domcontentloaded",
                timeout=5_000,
            )
            self.assertIsNotNone(response)
            self.assertEqual(response.status, 200)
            self.assertTrue(
                _HangingImageHandler.request_started.wait(timeout=1),
                "The slow-image seam was not exercised",
            )

            pending_started_at = monotonic()
            core_selectors = {
                ".hero-copy": "有状态路由器",
                "#value": "控制权",
                "#workflow": "确认产品问题",
                "#ownership": "Matt",
                "#dependencies": "grill-me",
                "#install": "$zero-to-one-product",
            }
            pending_text = {}
            for selector, required_text in core_selectors.items():
                with self.subTest(pending_image_selector=selector):
                    content = page.locator(selector)
                    self.assertEqual(content.count(), 1)
                    expect(content).to_be_visible(timeout=700)
                    pending_text[selector] = content.inner_text()
                    self.assertIn(required_text, pending_text[selector])

            page.wait_for_timeout(1_550)
            self.assertGreaterEqual(monotonic() - pending_started_at, 1.5)
            self.assertFalse(_HangingImageHandler.response_finished.is_set())
            for selector, expected_text in pending_text.items():
                content = page.locator(selector)
                expect(content).to_be_visible(timeout=700)
                self.assertEqual(content.inner_text(), expected_text)

            _HangingImageHandler.release_response.set()
            self.assertTrue(
                _HangingImageHandler.response_finished.wait(timeout=1),
                "The delayed image response did not finish",
            )
            page.wait_for_load_state("load", timeout=2_000)
            for selector, expected_text in pending_text.items():
                content = page.locator(selector)
                expect(content).to_be_visible(timeout=700)
                self.assertEqual(content.inner_text(), expected_text)

            self.assertEqual(console_errors, [])
            self.assertEqual(page_errors, [])
            self.assertEqual(failed_requests, [])
        finally:
            _HangingImageHandler.release_response.set()
            hanging_server.shutdown()
            hanging_server.server_close()
            hanging_thread.join(timeout=2)


if __name__ == "__main__":
    import unittest

    unittest.main()
