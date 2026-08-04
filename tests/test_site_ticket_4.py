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
        ownership = page.locator("#ownership")

        self.assertEqual(ownership.count(), 1, "Missing #ownership section")
        ownership_text = ownership.inner_text()
        expected_responsibilities = {
            "Matt": ("产品形成", "整票审查"),
            "Router": ("分类", "证据恢复", "Git gate", "有界执行"),
            "Superpowers": (
                "隔离",
                "单票计划",
                "TDD",
                "常规调试",
                "完成证据",
                "分支收尾",
            ),
        }
        for role, responsibilities in expected_responsibilities.items():
            with self.subTest(role=role):
                self.assertIn(role, ownership_text)
                for responsibility in responsibilities:
                    self.assertIn(responsibility, ownership_text)

    def test_guardrails_cover_execution_debugging_and_authorization(self):
        page = self.open_page()
        guardrails = page.locator("#guardrails")

        self.assertEqual(guardrails.count(), 1, "Missing #guardrails section")
        guardrails_text = guardrails.inner_text()
        compact_guardrails_text = "".join(guardrails_text.split())

        expected_rules = (
            "同阶段一个主流程",
            "产品发现不叠加 brainstorming",
            "正式编码只使用 Superpowers test-driven-development",
            "不使用 Matt tdd / implement",
            "常规调试使用 systematic-debugging",
            "仅有明确升级证据才使用 diagnosing-bugs",
        )
        for rule in expected_rules:
            with self.subTest(rule=rule):
                self.assertIn("".join(rule.split()), compact_guardrails_text)

        review_order = (
            "新实现者→RED–GREEN–REFACTOR→规格审查→质量审查→整票code-review"
        )
        self.assertIn(review_order, compact_guardrails_text)

        for gated_action in (
            "外部写入",
            "Issue Tracker",
            "worktree",
            "凭证",
            "破坏性操作",
            "提交",
            "推送",
            "部署",
        ):
            with self.subTest(gated_action=gated_action):
                self.assertIn("".join(gated_action.split()), compact_guardrails_text)
        self.assertIn("授权门", guardrails_text)

    def test_workflow_visuals_use_stable_intrinsic_image_contracts(self):
        page = self.open_page()

        for visual in ("fixed-route", "role-router"):
            with self.subTest(visual=visual):
                image = page.locator(f"img[data-visual='{visual}']")
                self.assertEqual(image.count(), 1, f"Missing {visual} visual")
                image_contract = image.evaluate(
                    """
                    element => ({
                      width: element.naturalWidth,
                      height: element.naturalHeight,
                      complete: element.complete,
                      loading: element.getAttribute("loading"),
                      alt: element.getAttribute("alt") ?? "",
                    })
                    """
                )
                self.assertEqual(image_contract["width"], 1440)
                self.assertEqual(image_contract["height"], 811)
                self.assertTrue(image_contract["complete"])
                self.assertEqual(image_contract["loading"], "lazy")
                self.assertGreaterEqual(len(image_contract["alt"].strip()), 12)

    def test_mobile_keeps_all_stages_and_new_sections_visible(self):
        page = self.open_page(width=390, height=844)

        scroll_width, client_width = page.evaluate(
            "[document.documentElement.scrollWidth, "
            "document.documentElement.clientWidth]"
        )
        self.assertLessEqual(scroll_width, client_width)

        owners = page.locator("#workflow [data-stage] .stage-owner")
        self.assertEqual(owners.count(), 13)
        owner_states = owners.evaluate_all(
            """
            elements => elements.map(element => ({
              visible: Boolean(
                element.offsetWidth
                || element.offsetHeight
                || element.getClientRects().length
              ),
              text: element.textContent.trim(),
            }))
            """
        )
        for index, owner_state in enumerate(owner_states, start=1):
            with self.subTest(stage=index):
                self.assertTrue(owner_state["visible"])
                self.assertTrue(owner_state["text"])

        for section_id in ("workflow", "ownership", "guardrails"):
            with self.subTest(section=section_id):
                section = page.locator(f"#{section_id}")
                self.assertEqual(section.count(), 1)
                self.assertTrue(section.is_visible())


if __name__ == "__main__":
    import unittest

    unittest.main()
