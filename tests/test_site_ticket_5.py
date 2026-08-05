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
        "Matt Pocock Skills 与 Superpowers 必须分别通过各自上游安装方式更新",
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

    def _copy_status_for(self, control):
        return control.locator(
            "xpath=ancestor::*[@data-command-block][1]"
        ).locator("[data-copy-status][aria-live]")

    def _copy_control_contract(self, control):
        return control.evaluate(
            """
            element => {
              const stableVisibleLabel = button => {
                const clone = button.cloneNode(true);
                clone.querySelectorAll("svg, [aria-hidden='true']")
                  .forEach(node => node.remove());
                return clone.textContent.replace(/\\s+/g, " ").trim();
              };
              const labelledBy = element.getAttribute("aria-labelledby");
              const accessibleLabel = labelledBy
                ? labelledBy.split(/\\s+/)
                  .map(id => document.getElementById(id)?.textContent ?? "")
                  .join(" ").replace(/\\s+/g, " ").trim()
                : (element.getAttribute("aria-label")
                  || stableVisibleLabel(element)).trim();
              const status = element.closest("[data-command-block]")
                ?.querySelector("[data-copy-status][aria-live]");
              return {
                visibleLabel: stableVisibleLabel(element),
                accessibleLabel,
                statusText: (status?.textContent ?? "")
                  .replace(/\\s+/g, " ").trim(),
              };
            }
            """
        )

    def _wait_for_copy_feedback_reset(self, page, control, expected_contract):
        control_handle = control.element_handle()
        self.assertIsNotNone(control_handle)
        page.wait_for_function(
            """
            ({element, expected}) => {
              const stableVisibleLabel = button => {
                const clone = button.cloneNode(true);
                clone.querySelectorAll("svg, [aria-hidden='true']")
                  .forEach(node => node.remove());
                return clone.textContent.replace(/\\s+/g, " ").trim();
              };
              const labelledBy = element.getAttribute("aria-labelledby");
              const accessibleLabel = labelledBy
                ? labelledBy.split(/\\s+/)
                  .map(id => document.getElementById(id)?.textContent ?? "")
                  .join(" ").replace(/\\s+/g, " ").trim()
                : (element.getAttribute("aria-label")
                  || stableVisibleLabel(element)).trim();
              const status = element.closest("[data-command-block]")
                ?.querySelector("[data-copy-status][aria-live]");
              const statusText = (status?.textContent ?? "")
                .replace(/\\s+/g, " ").trim();
              return stableVisibleLabel(element) === expected.visibleLabel
                && accessibleLabel === expected.accessibleLabel
                && statusText === expected.statusText;
            }
            """,
            arg={"element": control_handle, "expected": expected_contract},
            timeout=3_000,
        )
        self.assertEqual(
            self._copy_control_contract(control),
            expected_contract,
        )

    def _assert_narrow_release_content_fits(self, page):
        narrow_content = page.locator(
            "#dependencies [data-skill], #install code[data-command]"
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
                documentWidth: document.documentElement.clientWidth,
              };
            })
            """
        )
        for item in narrow_contracts:
            self.assertTrue(item["text"])
            self.assertTrue(item["visible"])
            self.assertGreaterEqual(item["left"], 0)
            self.assertLessEqual(item["right"], item["documentWidth"] + 0.5)
            self.assertLessEqual(item["scrollWidth"], item["clientWidth"] + 1)
        scroll_width, client_width = page.evaluate(
            "[document.documentElement.scrollWidth, "
            "document.documentElement.clientWidth]"
        )
        self.assertEqual(scroll_width, client_width)

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

        expected_phase_commands = {
            "matt": ["npx skills@latest add mattpocock/skills"],
            "superpowers": ["/plugins"],
            "router": [
                "codex plugin marketplace add nuts-and-bytes/zero-to-one-product",
                "codex plugin add zero-to-one-product@zero-to-one-product",
            ],
            "update": [
                "codex plugin marketplace upgrade zero-to-one-product"
            ],
            "use": [
                "$zero-to-one-product <你的产品想法或当前 0→1 目标>"
            ],
            "troubleshoot": [],
        }
        for phase_name, expected_commands in expected_phase_commands.items():
            with self.subTest(command_phase=phase_name):
                phase = install.locator(
                    f"[data-install-phase='{phase_name}']"
                )
                self.assertEqual(phase.count(), 1)
                phase_commands = phase.locator(
                    "code[data-command]"
                ).evaluate_all(
                    "elements => elements.map(element => "
                    "element.textContent.trim().replace(/\\s+/g, ' '))"
                )
                self.assertEqual(phase_commands, expected_commands)
                self.assertEqual(set(phase_commands), set(expected_commands))

        install_rules = {
            " ".join(text.split())
            for text in install.locator("[data-install-rule]").all_text_contents()
        }
        self.assertEqual(install_rules, self.INSTALL_RULES)

        install_text = " ".join(install.inner_text().split())
        self.assertRegex(install_text, r"Matt.*Superpowers.*Zero-to-One Product")
        for rejected_meaning in (
            "无需分别通过各自上游安装方式更新",
            "不必分别通过各自上游安装方式更新",
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
        pointer_initial_contracts = [
            self._copy_control_contract(controls.nth(index))
            for index in range(controls.count())
        ]

        for index, expected_command in enumerate(self.COMMANDS):
            with self.subTest(command=expected_command):
                control = controls.nth(index)
                initial_contract = pointer_initial_contracts[index]
                self.assertTrue(initial_contract["visibleLabel"])
                self.assertTrue(initial_contract["accessibleLabel"])
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
                control_box = control.bounding_box()
                self.assertIsNotNone(control_box)
                self.assertGreaterEqual(control_box["width"], 44)
                self.assertGreaterEqual(control_box["height"], 44)

                control.click()
                expect(status).to_contain_text("已复制", timeout=700)
                expect(status).to_be_visible(timeout=700)
                self.assertTrue(
                    control.evaluate("element => element === document.activeElement")
                )
                self.assertEqual(
                    page.evaluate("navigator.clipboard.readText()"),
                    expected_command,
                )
        for control_index in range(controls.count()):
            self._wait_for_copy_feedback_reset(
                page,
                controls.nth(control_index),
                pointer_initial_contracts[control_index],
            )

        page.reload(wait_until="networkidle", timeout=5_000)
        controls = page.locator(
            "#install button[type='button'][data-copy-command]"
        )
        keyboard_initial_contracts = [
            self._copy_control_contract(controls.nth(index))
            for index in range(controls.count())
        ]
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
            active_initial_contract = keyboard_initial_contracts[
                len(reached_commands) - 1
            ]
            self.assertTrue(active_control.evaluate("el => el === document.activeElement"))
            status = self._copy_status_for(active_control)

            for key in ("Enter", "Space"):
                page.evaluate("navigator.clipboard.writeText('')")
                page.keyboard.press(key)
                expect(status).to_contain_text("已复制", timeout=700)
                expect(status).to_be_visible(timeout=700)
                self.assertTrue(
                    active_control.evaluate(
                        "element => element === document.activeElement"
                    )
                )
                self.assertEqual(
                    page.evaluate("navigator.clipboard.readText()"),
                    active_command,
                )
                self._wait_for_copy_feedback_reset(
                    page,
                    active_control,
                    active_initial_contract,
                )
            if len(reached_commands) == len(self.COMMANDS):
                break
        self.assertEqual(reached_commands, self.COMMANDS)

        page.reload(wait_until="networkidle", timeout=5_000)
        page.evaluate(
            """
            () => {
              Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: undefined,
              });
              window.__fallbackCopySelections = [];
              document.execCommand = command => {
                if (command !== "copy") {
                  return false;
                }
                const active = document.activeElement;
                const selectedText = active
                  && typeof active.selectionStart === "number"
                  ? active.value.slice(active.selectionStart, active.selectionEnd)
                  : window.getSelection().toString();
                window.__fallbackCopySelections.push(selectedText);
                return true;
              };
            }
            """
        )
        fallback_controls = page.locator(
            "#install button[type='button'][data-copy-command]"
        )
        self.assertEqual(fallback_controls.count(), len(self.COMMANDS))
        fallback_initial_contracts = [
            self._copy_control_contract(fallback_controls.nth(index))
            for index in range(fallback_controls.count())
        ]
        for index, expected_command in enumerate(self.COMMANDS):
            with self.subTest(fallback_command=expected_command):
                control = fallback_controls.nth(index)
                status = self._copy_status_for(control)
                control.click()
                expect(status).to_contain_text("已复制", timeout=700)
                expect(status).to_be_visible(timeout=700)
                self.assertTrue(
                    control.evaluate("element => element === document.activeElement")
                )
                self.assertEqual(
                    page.evaluate("window.__fallbackCopySelections.at(-1)"),
                    expected_command,
                )
        for control_index in range(fallback_controls.count()):
            self._wait_for_copy_feedback_reset(
                page,
                fallback_controls.nth(control_index),
                fallback_initial_contracts[control_index],
            )

        page.reload(wait_until="networkidle", timeout=5_000)
        page.evaluate(
            """
            () => {
              Object.defineProperty(navigator.clipboard, "writeText", {
                configurable: true,
                value: () => Promise.reject(
                  new DOMException("clipboard denied", "NotAllowedError")
                ),
              });
              window.__fallbackCopySelections = [];
              document.execCommand = command => {
                if (command !== "copy") {
                  return false;
                }
                const active = document.activeElement;
                const selectedText = active
                  && typeof active.selectionStart === "number"
                  ? active.value.slice(active.selectionStart, active.selectionEnd)
                  : window.getSelection().toString();
                window.__fallbackCopySelections.push(selectedText);
                return true;
              };
            }
            """
        )
        rejected_api_control = page.locator(
            "#install button[type='button'][data-copy-command]"
        ).last
        rejected_api_initial_contract = self._copy_control_contract(
            rejected_api_control
        )
        rejected_api_status = self._copy_status_for(rejected_api_control)
        rejected_api_control.click()
        expect(rejected_api_status).to_contain_text("已复制", timeout=700)
        expect(rejected_api_status).to_be_visible(timeout=700)
        self.assertTrue(
            rejected_api_control.evaluate(
                "element => element === document.activeElement"
            )
        )
        self.assertEqual(
            page.evaluate("window.__fallbackCopySelections.at(-1)"),
            self.COMMANDS[-1],
        )
        self._wait_for_copy_feedback_reset(
            page,
            rejected_api_control,
            rejected_api_initial_contract,
        )

        page.reload(wait_until="networkidle", timeout=5_000)
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
        rejected_initial_contract = self._copy_control_contract(
            rejected_control
        )
        rejected_status = self._copy_status_for(rejected_control)
        rejected_control.click()
        expect(rejected_status).to_contain_text("复制失败", timeout=700)
        expect(rejected_status).to_be_visible(timeout=700)
        self.assertTrue(
            rejected_control.evaluate(
                "element => element === document.activeElement"
            )
        )
        self.assertNotIn("已复制", rejected_status.inner_text())
        self.assertEqual(
            page.evaluate("navigator.clipboard.readText()"),
            "sentinel",
        )
        self._wait_for_copy_feedback_reset(
            page,
            rejected_control,
            rejected_initial_contract,
        )

    def test_copy_fallback_restores_selection_and_contains_exec_errors(self):
        page = self.open_page(reduced_motion="reduce")
        page_errors = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        original_selection = page.evaluate(
            """
            () => {
              const textNode = document.querySelector(".hero-copy h1").firstChild;
              const range = document.createRange();
              range.setStart(textNode, 0);
              range.setEnd(textNode, 4);
              const selection = window.getSelection();
              selection.removeAllRanges();
              selection.addRange(range);
              window.__selectionContract = () => {
                const current = window.getSelection();
                return {
                  count: current.rangeCount,
                  text: current.toString(),
                  ranges: Array.from(
                    {length: current.rangeCount},
                    (_, index) => {
                      const item = current.getRangeAt(index);
                      return {
                        startText: item.startContainer.nodeValue,
                        startOffset: item.startOffset,
                        endText: item.endContainer.nodeValue,
                        endOffset: item.endOffset,
                      };
                    }
                  ),
                };
              };
              return window.__selectionContract();
            }
            """
        )
        page.evaluate(
            """
            () => {
              Object.defineProperty(navigator, "clipboard", {
                configurable: true,
                value: undefined,
              });
              document.execCommand = command => command === "copy";
            }
            """
        )
        control = page.locator(
            "#install button[type='button'][data-copy-command]"
        ).first
        initial_contract = self._copy_control_contract(control)
        status = self._copy_status_for(control)

        control.click()
        expect(status).to_contain_text("已复制", timeout=700)
        self.assertEqual(
            page.evaluate("window.__selectionContract()"),
            original_selection,
        )
        self._wait_for_copy_feedback_reset(
            page,
            control,
            initial_contract,
        )

        page.evaluate(
            """
            () => {
              document.execCommand = () => {
                throw new Error("copy command exploded");
              };
            }
            """
        )
        control.click()
        expect(status).to_contain_text("复制失败", timeout=700)
        expect(status).to_be_visible(timeout=700)
        self.assertEqual(
            page.evaluate("window.__selectionContract()"),
            original_selection,
        )
        self.assertEqual(page_errors, [])
        self._wait_for_copy_feedback_reset(
            page,
            control,
            initial_contract,
        )

    def test_latest_copy_operation_owns_feedback_and_reset_timer(self):
        page = self.open_page(reduced_motion="reduce")
        page.evaluate(
            """
            () => {
              window.__copyDeferred = [];
              Object.defineProperty(navigator.clipboard, "writeText", {
                configurable: true,
                value: command => new Promise((resolve, reject) => {
                  window.__copyDeferred.push({command, resolve, reject});
                }),
              });
              document.execCommand = () => false;
            }
            """
        )
        control = page.locator(
            "#install button[type='button'][data-copy-command]"
        ).first
        initial_contract = self._copy_control_contract(control)
        status = self._copy_status_for(control)

        control.click()
        control.click()
        page.wait_for_function("window.__copyDeferred.length === 2", timeout=700)
        page.evaluate(
            "window.__copyDeferred[1].reject("
            "new DOMException('latest denied', 'NotAllowedError'))"
        )
        expect(status).to_contain_text("复制失败", timeout=700)
        latest_failure_contract = self._copy_control_contract(control)
        self.assertIn("复制失败", latest_failure_contract["visibleLabel"])
        self.assertIn("复制失败", latest_failure_contract["accessibleLabel"])
        self.assertIn("复制失败", latest_failure_contract["statusText"])

        page.evaluate("window.__copyDeferred[0].resolve()")
        page.wait_for_timeout(100)
        self.assertEqual(
            self._copy_control_contract(control),
            latest_failure_contract,
            "An older completion must not overwrite the latest failure",
        )

        page.wait_for_timeout(900)
        control.click()
        page.wait_for_function("window.__copyDeferred.length === 3", timeout=700)
        page.evaluate("window.__copyDeferred[2].resolve()")
        expect(status).to_contain_text("已复制", timeout=700)
        latest_success_contract = self._copy_control_contract(control)
        self.assertIn("已复制", latest_success_contract["visibleLabel"])

        page.wait_for_timeout(800)
        self.assertEqual(
            self._copy_control_contract(control),
            latest_success_contract,
            "A retry must cancel the previous operation's reset timer",
        )
        self._wait_for_copy_feedback_reset(
            page,
            control,
            initial_contract,
        )

    def test_internal_navigation_cleans_only_temporary_target_tabindex(self):
        page = self.open_page(reduced_motion="reduce")

        target = page.locator("#value")
        self.assertIsNone(target.get_attribute("tabindex"))
        page.locator("#primary-navigation a[href='#value']").click()
        self.assertTrue(target.evaluate("element => element === document.activeElement"))
        self.assertEqual(target.get_attribute("tabindex"), "-1")
        page.evaluate("document.activeElement.blur()")
        expect(target).not_to_have_attribute("tabindex", "-1")
        self.assertIsNone(target.get_attribute("tabindex"))

        existing_target = page.locator("#classifier")
        existing_target.evaluate("element => element.setAttribute('tabindex', '0')")
        page.locator("#primary-navigation a[href='#classifier']").click()
        self.assertTrue(
            existing_target.evaluate("element => element === document.activeElement")
        )
        self.assertEqual(existing_target.get_attribute("tabindex"), "0")
        page.evaluate("document.activeElement.blur()")
        self.assertEqual(existing_target.get_attribute("tabindex"), "0")

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

        copy_controls = install.locator("[data-copy-command]")
        copy_statuses = install.locator("[data-copy-status][aria-live]")
        self.assertEqual(copy_controls.count(), len(self.COMMANDS))
        self.assertEqual(copy_statuses.count(), len(self.COMMANDS))
        self.assertTrue(
            copy_controls.evaluate_all(
                "elements => elements.every(element => "
                "!element.checkVisibility())"
            )
        )
        self.assertTrue(
            copy_statuses.evaluate_all(
                "elements => elements.every(element => "
                "!element.checkVisibility())"
            )
        )
        reached_copy_control = False
        for _tab_stop in range(
            page.locator("a[href], button, [tabindex]").count() + 2
        ):
            page.keyboard.press("Tab")
            reached_copy_control = reached_copy_control or page.evaluate(
                "Boolean(document.activeElement?.dataset.copyCommand)"
            )
        self.assertFalse(reached_copy_control)

        self.browser_context.close()
        del self.browser_context
        enhanced_page = self.open_page(reduced_motion="reduce")
        enhanced_install = self._required_section(enhanced_page, "install")
        self.assertEqual(
            enhanced_install.locator("[data-copy-command]:visible").count(),
            len(self.COMMANDS),
        )
        self.assertTrue(
            enhanced_install.locator(
                "[data-copy-status][aria-live]"
            ).evaluate_all(
                "elements => elements.every(element => "
                "element.checkVisibility())"
            )
        )

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
            "meta[property='og:image:alt']": (
                "Zero-to-One Product 固定十三阶段路线与三方职责示意"
            ),
            "meta[property='og:locale']": "zh_CN",
            "meta[name='twitter:card']": "summary_large_image",
            "meta[name='twitter:title']": self.PAGE_TITLE,
            "meta[name='twitter:description']": self.DESCRIPTION,
            "meta[name='twitter:image']": self.SHARE_IMAGE_URL,
            "meta[name='twitter:image:alt']": (
                "Zero-to-One Product 固定十三阶段路线与三方职责示意"
            ),
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
        navigation_hrefs = page.locator(
            "#primary-navigation a"
        ).evaluate_all(
            "elements => elements.map(element => element.getAttribute('href'))"
        )
        required_navigation_hrefs = {
            "#value",
            "#classifier",
            "#workflow",
            "#ownership",
            "#guardrails",
            "#dependencies",
            "#install",
        }
        self.assertTrue(
            required_navigation_hrefs.issubset(set(navigation_hrefs))
        )
        self.assertEqual(len(navigation_hrefs), len(set(navigation_hrefs)))
        self.assertGreaterEqual(
            page.locator(
                "a[href='https://github.com/nuts-and-bytes/zero-to-one-product']"
            ).count(),
            1,
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
        self.assertGreaterEqual(
            internal_navigation.count(),
            len(required_navigation_hrefs),
        )
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
                    visible: target.checkVisibility({
                      checkOpacity: true,
                      checkVisibilityCSS: true,
                    }),
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
            self.assertTrue(target_contract["visible"])
            self.assertTrue(target_contract["intersectsViewport"])
            self.assertTrue(target_contract["focusIsReasonable"])

        page.evaluate("document.activeElement?.blur()")
        page.goto(
            f"{self.base_url}/",
            wait_until="networkidle",
            timeout=5_000,
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
            expected_focus = page.locator(
                f"[data-acceptance-focus-order='{expected_index}']"
            )
            before_focus = expected_focus.evaluate(
                """
                element => {
                  const style = getComputedStyle(element);
                  return {
                    outlineStyle: style.outlineStyle,
                    outlineWidth: style.outlineWidth,
                    outlineColor: style.outlineColor,
                    boxShadow: style.boxShadow,
                  };
                }
                """
            )
            page.keyboard.press("Tab")
            focus_contract = page.evaluate(
                """
                () => {
                  const element = document.activeElement;
                  const style = getComputedStyle(element);
                  const colorHasAlpha = color => {
                    if (color === "transparent") {
                      return false;
                    }
                    const values = color.match(/[\\d.]+/g) || [];
                    return values.length < 4 || Number(values[3]) > 0;
                  };
                  const shadowHasAlpha = shadow => {
                    if (shadow === "none") {
                      return false;
                    }
                    const colors = Array.from(
                      shadow.matchAll(/rgba?\\(([^)]+)\\)/g)
                    );
                    return colors.length === 0 || colors.some(match => {
                      const values = match[1].match(/[\\d.]+/g) || [];
                      return values.length < 4 || Number(values[3]) > 0;
                    });
                  };
                  const rect = element.getBoundingClientRect();
                  return {
                    order: Number(element.dataset.acceptanceFocusOrder),
                    outlineStyle: style.outlineStyle,
                    outlineWidth: Number.parseFloat(style.outlineWidth),
                    outlineWidthText: style.outlineWidth,
                    outlineColor: style.outlineColor,
                    boxShadow: style.boxShadow,
                    outlineVisible:
                      style.outlineStyle !== "none"
                      && Number.parseFloat(style.outlineWidth) >= 2
                      && colorHasAlpha(style.outlineColor),
                    shadowVisible: shadowHasAlpha(style.boxShadow),
                    width: rect.width,
                    height: rect.height,
                  };
                }
                """
            )
            self.assertEqual(focus_contract["order"], expected_index)
            outline_changed = (
                focus_contract["outlineStyle"] != before_focus["outlineStyle"]
                or focus_contract["outlineWidthText"]
                != before_focus["outlineWidth"]
                or focus_contract["outlineColor"]
                != before_focus["outlineColor"]
            )
            shadow_changed = (
                focus_contract["boxShadow"] != before_focus["boxShadow"]
            )
            self.assertTrue(outline_changed or shadow_changed)
            self.assertTrue(
                focus_contract["outlineVisible"]
                or (shadow_changed and focus_contract["shadowVisible"]),
                f"Missing visible focus indicator at tab stop {expected_index}",
            )
            self.assertGreater(focus_contract["width"], 0)
            self.assertGreater(focus_contract["height"], 0)

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
                        self._assert_narrow_release_content_fits(page)
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
        try:
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
                lambda request: failed_requests.append(
                    (request.url, request.failure)
                ),
            )

            def delay_images(route, request):
                if request.resource_type == "image":
                    route.continue_(url=slow_image_url)
                else:
                    route.continue_()

            page.route("**/*", delay_images)
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
            if _HangingImageHandler.request_started.is_set():
                _HangingImageHandler.response_finished.wait(timeout=1)
            if hasattr(self, "browser_context"):
                self.browser_context.close()
                del self.browser_context
            if hanging_thread.is_alive():
                hanging_server.shutdown()
            hanging_server.server_close()
            hanging_thread.join(timeout=2)
            self.assertFalse(
                hanging_thread.is_alive(),
                "Hanging-image server thread did not exit",
            )

    def test_core_content_survives_intentional_image_failures(self):
        core_selectors = {
            ".hero-copy": "有状态路由器",
            "#value": "控制权",
            "#workflow": "确认产品问题",
            "#ownership": "Matt",
            "#dependencies": "grill-me",
            "#install": "$zero-to-one-product",
        }
        baseline_page = self.open_page(
            width=390,
            height=844,
            reduced_motion="reduce",
        )
        baseline_text = {}
        for selector, required_text in core_selectors.items():
            with self.subTest(baseline_selector=selector):
                content = baseline_page.locator(selector)
                self.assertEqual(content.count(), 1)
                expect(content).to_be_visible(timeout=700)
                baseline_text[selector] = content.inner_text()
                self.assertIn(required_text, baseline_text[selector])
        self.browser_context.close()
        del self.browser_context

        intentionally_aborted = set()
        failed_requests = []
        console_errors = []
        page_errors = []
        self.browser_context = self.browser.new_context(
            viewport={"width": 390, "height": 844},
            reduced_motion="reduce",
        )
        page = self.browser_context.new_page()
        page.on(
            "requestfailed",
            lambda request: failed_requests.append((request.url, request.failure)),
        )
        page.on(
            "console",
            lambda message: console_errors.append(
                (message.text, message.location.get("url", ""))
            )
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: page_errors.append(str(error)))

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

        images = page.locator("img")
        self.assertGreater(images.count(), 0)
        image_sources = images.evaluate_all(
            """
            elements => elements.map(element =>
              element.currentSrc || element.src
            )
            """
        )
        self.assertTrue(all(image_sources))
        for image_index in range(images.count()):
            images.nth(image_index).scroll_into_view_if_needed(timeout=700)

        failure_deadline = monotonic() + 3
        missing_sources = list(image_sources)
        while missing_sources and monotonic() < failure_deadline:
            failed_urls = {url for url, _failure in failed_requests}
            missing_sources = [
                source for source in image_sources if source not in failed_urls
            ]
            if missing_sources:
                page.wait_for_timeout(50)
        self.assertEqual(
            missing_sources,
            [],
            f"Missing intentional image failures for: {missing_sources}",
        )

        failed_urls = {url for url, _failure in failed_requests}
        self.assertTrue(failed_urls)
        self.assertTrue(failed_urls.issubset(intentionally_aborted))
        for image_source in image_sources:
            self.assertIn(
                image_source,
                failed_urls,
                f"Image source did not produce an intentional failure: "
                f"{image_source}",
            )
        for failed_url, failure in failed_requests:
            self.assertIn(failed_url, intentionally_aborted)
            self.assertRegex(failure or "", r"ERR_FAILED|aborted|failed")

        for selector, required_text in core_selectors.items():
            with self.subTest(failed_image_selector=selector):
                content = page.locator(selector)
                self.assertEqual(content.count(), 1)
                expect(content).to_be_visible(timeout=700)
                failed_text = content.inner_text()
                self.assertIn(required_text, failed_text)
                self.assertIn(selector, baseline_text)
                self.assertEqual(failed_text, baseline_text[selector])

        self._assert_narrow_release_content_fits(page)
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


if __name__ == "__main__":
    import unittest

    unittest.main()
