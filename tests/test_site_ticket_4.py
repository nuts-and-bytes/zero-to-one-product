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
            elements => elements.map(stage => [
              stage.querySelector(".stage-number")?.textContent.trim() ?? "",
              stage.querySelector(".stage-title")?.textContent.trim() ?? "",
              stage.querySelector(".stage-mechanism")?.textContent.trim() ?? "",
              stage.querySelector(".stage-owner")?.textContent.trim() ?? "",
            ])
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

        def item_text(name):
            item = page.locator(f"#guardrails [data-guardrail='{name}']")
            self.assertEqual(item.count(), 1, f"Missing {name} guardrail")
            return normalized(item.inner_text())

        single_owner = item_text("single-owner")
        for pattern in (
            r"同一阶段.*只有.*一个.*主流程",
            r"产品发现.*不.*brainstorming",
            r"正式编码.*只.*Superpowers.*test-driven-development",
            r"禁止.*Matt.*tdd",
            r"禁止.*Matt.*implement",
        ):
            self.assertRegex(single_owner, pattern)

        planning_boundary = item_text("planning-boundary")
        self.assertIn(
            "规格和 Tickets 完成后，才能运行 writing-plans",
            planning_boundary,
        )
        for pattern in (
            r"writing-plans.*只.*一个.*Ticket",
            r"to-tickets.*纵向.*Tickets.*writing-plans.*单个",
        ):
            self.assertRegex(planning_boundary, pattern)

        bounded_execution = item_text("bounded-execution")
        for pattern in (
            r"一个.*Ticket.*批准.*计划.*按序",
            r"独立.*新实现者",
            r"RED.*GREEN.*REFACTOR.*规格审查.*质量审查.*code-review",
            r"规格审查.*未通过.*修复.*重复.*通过.*质量审查.*未通过.*修复.*重复.*通过",
            r"完成.*交还.*Router",
            r"不得.*直接.*verification-before-completion.*finishing-a-development-branch",
            r"禁止.*完整.*subagent-driven-development.*executing-plans",
        ):
            self.assertRegex(bounded_execution, pattern)

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
        self.assertIn(
            "以下所有受控操作仍必须逐项经过独立授权门",
            authorization,
        )
        self.assertNotRegex(authorization, r"(?:不受|无需).*授权")
        actions = (
            "工作区",
            "目录创建",
            "Git 初始化",
            "外部写入",
            "Issue Tracker",
            "worktree",
            "凭证",
            "破坏性操作",
            "commit",
            "push",
            "PR",
            "deploy",
            "release",
            "外部通信",
            "独立授权门",
        )
        for action in actions:
            self.assertIn(action, authorization)
        self.assertRegex(
            authorization,
            r"自动路由.*只.*免除.*路由确认.*不.*扩大.*权限",
        )
        self.assertRegex(
            authorization,
            r"工作区.*Git 初始化.*外部写入.*Issue Tracker.*worktree.*凭证.*破坏性.*commit.*push.*PR.*deploy.*release.*外部通信.*独立授权门",
        )

    def test_workflow_visuals_use_stable_intrinsic_image_contracts(self):
        page = self.open_page()

        for visual in ("fixed-route", "role-router"):
            with self.subTest(visual=visual):
                image = page.locator(f"img[data-visual='{visual}']")
                self.assertEqual(image.count(), 1, f"Missing {visual} visual")
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
                      const hit = document.elementFromPoint(centerX, centerY);
                      return {
                        width: element.naturalWidth,
                        height: element.naturalHeight,
                        complete: element.complete,
                        loading: element.getAttribute("loading"),
                        alt: element.getAttribute("alt") ?? "",
                        opacity: Number.parseFloat(style.opacity),
                        visibility: style.visibility,
                        centerInViewport:
                          centerX >= 0
                          && centerX <= window.innerWidth
                          && centerY >= 0
                          && centerY <= window.innerHeight,
                        centerHitsImage:
                          hit === element || (hit !== null && element.contains(hit)),
                      };
                    }
                    """
                )
                self.assertEqual(image_contract["width"], 1440)
                self.assertEqual(image_contract["height"], 811)
                self.assertTrue(image_contract["complete"])
                self.assertEqual(image_contract["loading"], "lazy")
                self.assertGreaterEqual(len(image_contract["alt"].strip()), 12)
                self.assertGreater(image_contract["opacity"], 0.01)
                self.assertEqual(image_contract["visibility"], "visible")
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
                  };
                }
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return {
                  text: element.textContent.trim(),
                  visible: element.checkVisibility({
                    checkOpacity: true,
                    checkVisibilityCSS: true,
                  }),
                  visibility: style.visibility,
                  opacity: Number.parseFloat(style.opacity),
                  width: rect.width,
                  height: rect.height,
                };
              };
              const documentWidth = document.documentElement.clientWidth;
              return elements.map(row => {
                const rect = row.getBoundingClientRect();
                return {
                  number: visibility(row.querySelector(".stage-number")),
                  title: visibility(row.querySelector(".stage-title")),
                  mechanism: visibility(row.querySelector(".stage-mechanism")),
                  owner: visibility(row.querySelector(".stage-owner")),
                  rowWidth: rect.width,
                  rowHeight: rect.height,
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


if __name__ == "__main__":
    import unittest

    unittest.main()
