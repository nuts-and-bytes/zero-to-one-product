from playwright.sync_api import expect

from tests.site_test_support import SiteBrowserTestCase


class Ticket4AcceptanceTests(SiteBrowserTestCase):
    EXPECTED_STAGES = [
        ("01", "确认产品问题", "grill-me / grill-with-docs", "Matt"),
        ("02", "拆解大型未知", "wayfinder", "Matt"),
        ("03", "补齐事实", "research", "Matt"),
        ("04", "验证关键不确定性", "prototype", "Matt"),
        ("05", "形成规格", "to-spec", "Matt"),
        ("06", "切成 Tickets", "to-tickets", "Matt"),
        ("07", "确认仓库状态", "zero-to-one-product", "Router"),
        ("08", "隔离工作区", "using-git-worktrees", "Superpowers"),
        ("09", "规划单个 Ticket", "writing-plans", "Superpowers"),
        ("10", "有界执行", "zero-to-one-product", "Router"),
        ("11", "整体代码审查", "code-review", "Matt"),
        (
            "12",
            "完成证据",
            "verification-before-completion",
            "Superpowers",
        ),
        (
            "13",
            "分支收尾",
            "finishing-a-development-branch",
            "Superpowers",
        ),
    ]

    def test_workflow_lists_the_exact_thirteen_stage_route(self):
        page = self.open_page()

        stages = page.locator("#workflow [data-stage]").evaluate_all(
            """
            elements => {
              const text = (stage, selector) =>
                (stage.querySelector(selector)?.textContent ?? "")
                  .trim()
                  .replace(/\\s+/g, " ");
              return elements.map(stage => [
                text(stage, ".stage-number"),
                text(stage, ".stage-title"),
                text(stage, ".stage-mechanism"),
                text(stage, ".stage-owner"),
              ]);
            }
            """
        )

        self.assertEqual(stages, [list(stage) for stage in self.EXPECTED_STAGES])

    def test_workflow_explains_evidence_based_resume_semantics(self):
        page = self.open_page()
        workflow = page.locator("#workflow")

        self.assertEqual(workflow.count(), 1, "Missing #workflow section")
        workflow_text = workflow.inner_text()
        self.assertIn("根据已有证据恢复到最靠后的未完成阶段", workflow_text)
        self.assertIn("不是每次重新 brainstorming", workflow_text)

    def test_ownership_assigns_each_role_its_full_responsibility(self):
        page = self.open_page()
        expected_responsibilities = {
            "matt": ("Matt", "产品形成", "困难调试", "整票审查"),
            "router": (
                "Router",
                "分类",
                "证据恢复",
                "Git gate",
                "有界执行",
                "阶段交还",
            ),
            "superpowers": (
                "Superpowers",
                "隔离",
                "单票技术计划",
                "TDD",
                "常规调试",
                "任务审查",
                "完成证据",
                "分支收尾",
            ),
        }
        for owner, expected_text in expected_responsibilities.items():
            with self.subTest(owner=owner):
                card = page.locator(f"#ownership [data-owner='{owner}']")
                self.assertEqual(card.count(), 1, f"Missing {owner} owner card")
                card_text = card.inner_text()
                for keyword in expected_text:
                    self.assertIn(keyword, card_text)

    def test_guardrails_cover_execution_debugging_and_authorization(self):
        page = self.open_page()

        def normalized(text):
            return " ".join(text.split())

        def contract_text(text):
            return "".join(
                character
                for character in normalized(text)
                if character.isalnum() or character == "-"
            )

        def item_text(name):
            item = page.locator(f"#guardrails [data-guardrail='{name}']")
            self.assertEqual(item.count(), 1, f"Missing {name} guardrail")
            return normalized(item.inner_text())

        def structured_rules(guardrail, attribute):
            rules = page.locator(
                f"#guardrails [data-guardrail='{guardrail}'] [{attribute}]"
            )
            return [normalized(text) for text in rules.all_text_contents()]

        single_owner = item_text("single-owner")
        normalized_single_owner = contract_text(single_owner)
        for positive_rule in (
            "同一阶段只有一个主流程",
            "产品发现阶段不使用 Superpowers brainstorming",
            "正式编码只使用 Superpowers test-driven-development",
            "禁止调用 Matt tdd",
            "禁止调用 Matt implement",
        ):
            self.assertIn(contract_text(positive_rule), normalized_single_owner)
        for rejected_rule in (
            "不禁止调用 Matt tdd",
            "不禁止调用 Matt implement",
            "正式编码不只使用 Superpowers test-driven-development",
            "仍可使用 Matt tdd",
            "仍可使用 Matt implement",
            "可以使用 Matt tdd",
            "可以使用 Matt implement",
        ):
            self.assertNotIn(contract_text(rejected_rule), normalized_single_owner)

        self.assertCountEqual(
            structured_rules("planning-boundary", "data-planning-rule"),
            (
                "规格和 Tickets 完成后，才能运行 writing-plans",
                "writing-plans 只服务一个 Ticket",
                "to-tickets 把已批准规格切成纵向 Tickets，"
                "writing-plans 只为其中单个 Ticket 生成技术计划",
            ),
        )

        self.assertCountEqual(
            structured_rules("bounded-execution", "data-execution-rule"),
            (
                "一个已选 Ticket 只有在计划批准后才能按序执行",
                "每个任务由独立的新实现者负责",
                "每个任务必须依次经过 RED、GREEN、REFACTOR、规格审查和质量审查",
                "规格审查未通过时必须修复并重复审查直至通过；"
                "之后质量审查未通过时必须修复并重复审查直至通过",
                "所有任务完成后必须交还 Router，再由 Matt 执行整票 code-review",
                "不得直接进入 verification-before-completion 或 "
                "finishing-a-development-branch",
                "禁止调用完整的 subagent-driven-development 或 executing-plans",
            ),
        )

        debugging = item_text("debugging")
        self.assertIn(
            "只有在出现间歇性、性能相关、难复现或无法解决等明确升级证据时，"
            "才升级到 diagnosing-bugs",
            debugging,
        )
        for pattern in (
            r"systematic-debugging.*常规",
            r"两个.*调试.*不得.*同时",
        ):
            self.assertRegex(debugging, pattern)

        authorization = item_text("authorization")
        normalized_authorization = contract_text(authorization)
        self.assertIn(
            contract_text("以下所有受控操作仍必须逐项经过独立授权门"),
            normalized_authorization,
        )
        for rejected_rule in ("不受独立授权门", "无需独立授权"):
            self.assertNotIn(
                contract_text(rejected_rule),
                normalized_authorization,
            )

        expected_actions = {
            "workspace-directory": ("工作区", "目录创建"),
            "git-init": ("Git", "初始化"),
            "external-write": ("外部写入",),
            "issue-tracker": ("Issue Tracker",),
            "worktree": ("worktree",),
            "credentials": ("凭证",),
            "destructive": ("破坏性操作",),
            "commit": ("commit",),
            "push": ("push",),
            "pr": ("PR",),
            "deploy-release": ("deploy", "release"),
            "external-communication": ("外部通信",),
        }
        action_items = page.locator(
            "#guardrails [data-guardrail='authorization'] "
            "[data-authorization-action]"
        )
        action_contracts = action_items.evaluate_all(
            """
            elements => elements.map(element => ({
              action: element.dataset.authorizationAction,
              text: element.textContent.trim().replace(/\\s+/g, " "),
            }))
            """
        )
        self.assertCountEqual(
            [item["action"] for item in action_contracts],
            expected_actions,
        )
        for item in action_contracts:
            with self.subTest(action=item["action"]):
                for keyword in expected_actions[item["action"]]:
                    self.assertIn(keyword, item["text"])
        self.assertRegex(
            authorization,
            r"自动路由.*只.*免除.*路由确认.*不.*扩大.*权限",
        )

    def test_workflow_visuals_use_stable_intrinsic_image_contracts(self):
        for visual in ("fixed-route", "role-router"):
            with self.subTest(visual=visual):
                for width, height in ((1280, 720), (390, 844)):
                    page = self.open_page(
                        width=width,
                        height=height,
                        reduced_motion="reduce",
                    )
                    try:
                        image = page.locator(f"img[data-visual='{visual}']")
                        self.assertEqual(
                            image.count(),
                            1,
                            f"Missing {visual} visual at {width}px",
                        )
                        image.scroll_into_view_if_needed(timeout=1_500)
                        image_handle = image.element_handle()
                        self.assertIsNotNone(image_handle)
                        page.wait_for_function(
                            "element => element.naturalWidth > 0",
                            arg=image_handle,
                            timeout=1_500,
                        )
                        expect(image).to_be_visible(timeout=1_500)
                        image_contract = image.evaluate(
                            """
                            element => {
                              const style = getComputedStyle(element);
                              const rect = element.getBoundingClientRect();
                              const centerX = rect.left + rect.width / 2;
                              const centerY = rect.top + rect.height / 2;
                              const hit = document.elementFromPoint(
                                centerX,
                                centerY
                              );
                              return {
                                width: element.naturalWidth,
                                height: element.naturalHeight,
                                complete: element.complete,
                                loading: element.getAttribute("loading"),
                                alt: element.getAttribute("alt") ?? "",
                                visible: element.checkVisibility({
                                  checkOpacity: true,
                                  checkVisibilityCSS: true,
                                }),
                                opacity: Number.parseFloat(style.opacity),
                                visibility: style.visibility,
                                centerInViewport:
                                  centerX >= 0
                                  && centerX <= window.innerWidth
                                  && centerY >= 0
                                  && centerY <= window.innerHeight,
                                centerHitsImage:
                                  hit === element
                                  || (hit !== null && element.contains(hit)),
                              };
                            }
                            """
                        )
                        self.assertEqual(image_contract["width"], 1440)
                        self.assertEqual(image_contract["height"], 811)
                        self.assertTrue(image_contract["complete"])
                        self.assertEqual(image_contract["loading"], "lazy")
                        self.assertGreaterEqual(
                            len(image_contract["alt"].strip()),
                            12,
                        )
                        self.assertTrue(image_contract["visible"])
                        self.assertGreater(image_contract["opacity"], 0.01)
                        self.assertEqual(
                            image_contract["visibility"],
                            "visible",
                        )
                        self.assertTrue(image_contract["centerInViewport"])
                        self.assertTrue(image_contract["centerHitsImage"])
                        box = image.bounding_box()
                        self.assertIsNotNone(box)
                        self.assertGreaterEqual(box["width"], 280)
                        self.assertGreaterEqual(box["height"], 150)
                        self.assertAlmostEqual(
                            box["height"] / box["width"],
                            811 / 1440,
                            delta=0.02,
                        )
                        if visual == "fixed-route":
                            for keyword in ("固定", "阶段", "路线"):
                                self.assertIn(keyword, image_contract["alt"])
                        else:
                            for role in ("Matt", "Router", "Superpowers"):
                                self.assertIn(role, image_contract["alt"])
                    finally:
                        self.browser_context.close()
                        del self.browser_context

    def test_mobile_keeps_all_stages_and_new_sections_visible(self):
        page = self.open_page(
            width=390,
            height=844,
            reduced_motion="reduce",
        )

        scroll_width, client_width = page.evaluate(
            "[document.documentElement.scrollWidth, "
            "document.documentElement.clientWidth]"
        )
        self.assertLessEqual(scroll_width, client_width)

        rows = page.locator("#workflow [data-stage]")
        self.assertEqual(rows.count(), 13, "Expected exactly 13 workflow rows")
        row_states = rows.evaluate_all(
            """
            elements => {
              const visibility = element => {
                if (!element) {
                  return {
                    text: "",
                    visible: false,
                    visibility: "missing",
                    opacity: 0,
                    width: 0,
                    height: 0,
                    intersectsViewport: false,
                    centerHitsElement: false,
                  };
                }
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                const hit = document.elementFromPoint(centerX, centerY);
                return {
                  text: element.textContent.trim().replace(/\\s+/g, " "),
                  visible: element.checkVisibility({
                    checkOpacity: true,
                    checkVisibilityCSS: true,
                  }),
                  visibility: style.visibility,
                  opacity: Number.parseFloat(style.opacity),
                  width: rect.width,
                  height: rect.height,
                  intersectsViewport:
                    rect.right > 0
                    && rect.left < window.innerWidth
                    && rect.bottom > 0
                    && rect.top < window.innerHeight,
                  centerHitsElement:
                    hit === element || (hit !== null && element.contains(hit)),
                };
              };
              const documentWidth = document.documentElement.clientWidth;
              return elements.map(row => {
                row.scrollIntoView({block: "center", inline: "nearest"});
                const rect = row.getBoundingClientRect();
                return {
                  number: visibility(row.querySelector(".stage-number")),
                  title: visibility(row.querySelector(".stage-title")),
                  mechanism: visibility(row.querySelector(".stage-mechanism")),
                  owner: visibility(row.querySelector(".stage-owner")),
                  rowWidth: rect.width,
                  rowHeight: rect.height,
                  documentTop: rect.top + window.scrollY,
                  documentBottom: rect.bottom + window.scrollY,
                  rowWithinDocument:
                    rect.left >= 0 && rect.right <= documentWidth + 0.5,
                };
              });
            }
            """
        )
        for row_index, row_state in enumerate(row_states, start=1):
            with self.subTest(row=row_index):
                self.assertGreater(row_state["rowWidth"], 0)
                self.assertGreater(row_state["rowHeight"], 0)
                self.assertTrue(row_state["rowWithinDocument"])
                for field in ("number", "title", "mechanism", "owner"):
                    field_state = row_state[field]
                    self.assertTrue(field_state["text"])
                    self.assertTrue(field_state["visible"])
                    self.assertEqual(field_state["visibility"], "visible")
                    self.assertGreater(field_state["opacity"], 0)
                    self.assertGreater(field_state["width"], 0)
                    self.assertGreater(field_state["height"], 0)
                    self.assertTrue(field_state["intersectsViewport"])
                    self.assertTrue(field_state["centerHitsElement"])

        for previous, current in zip(row_states, row_states[1:]):
            self.assertGreater(
                current["documentTop"],
                previous["documentTop"],
            )
            self.assertGreaterEqual(
                current["documentTop"],
                previous["documentBottom"],
            )

        sections = page.locator("#workflow, #ownership, #guardrails")
        self.assertEqual(sections.count(), 3)
        section_states = sections.evaluate_all(
            """
            elements => elements.map(element => {
              const rect = element.getBoundingClientRect();
              return {
                id: element.id,
                visible: element.checkVisibility({
                  checkOpacity: true,
                  checkVisibilityCSS: true,
                }),
                width: rect.width,
                height: rect.height,
              };
            })
            """
        )
        for section_state in section_states:
            with self.subTest(section=section_state["id"]):
                self.assertTrue(section_state["visible"])
                self.assertGreater(section_state["width"], 0)
                self.assertGreater(section_state["height"], 0)

    def test_tablet_navigation_keeps_every_link_on_one_line(self):
        page = self.open_page(width=768, height=1024)

        header = page.locator("[data-site-header]")
        navigation = page.get_by_role("navigation", name="主要导航")
        links = navigation.locator("a")

        self.assertEqual(links.count(), 7)
        expect(navigation).to_be_visible()
        header_box = header.bounding_box()
        self.assertIsNotNone(header_box)
        self.assertLessEqual(header_box["height"], 72)

        link_contracts = links.evaluate_all(
            """
            elements => elements.map(element => {
              const range = document.createRange();
              range.selectNodeContents(element);
              const rect = element.getBoundingClientRect();
              return {
                text: element.textContent.trim(),
                visible: element.checkVisibility({
                  checkOpacity: true,
                  checkVisibilityCSS: true,
                }),
                textLineCount: range.getClientRects().length,
                width: rect.width,
                height: rect.height,
              };
            })
            """
        )
        for link in link_contracts:
            with self.subTest(link=link["text"]):
                self.assertTrue(link["visible"])
                self.assertEqual(link["textLineCount"], 1)
                self.assertGreater(link["width"], 0)
                self.assertGreater(link["height"], 0)

        scroll_width, client_width = page.evaluate(
            "[document.documentElement.scrollWidth, "
            "document.documentElement.clientWidth]"
        )
        self.assertLessEqual(scroll_width, client_width)


if __name__ == "__main__":
    import unittest

    unittest.main()
