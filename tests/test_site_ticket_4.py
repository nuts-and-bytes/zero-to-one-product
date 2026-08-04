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
        ownership = page.locator("#ownership")

        self.assertEqual(ownership.count(), 1, "Missing #ownership section")
        ownership_text = ownership.inner_text()
        expected_responsibilities = {
            "Matt": ("产品形成", "困难调试", "整票审查"),
            "Router": (
                "分类",
                "证据恢复",
                "Git gate",
                "有界执行",
                "阶段交还",
            ),
            "Superpowers": (
                "隔离",
                "单票技术计划",
                "TDD",
                "常规调试",
                "任务审查",
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

        expected_process_rules = (
            "同阶段一个主流程",
            "产品发现不叠加 brainstorming",
            "正式编码只使用 Superpowers test-driven-development",
            "writing-plans 只在规格和 Tickets 完成后运行，且仅服务一个 Ticket",
            "to-tickets 负责切票，writing-plans 负责单票技术计划",
            "禁止使用 Matt tdd / implement",
            "禁止完整运行 subagent-driven-development / executing-plans",
            "普通调试与困难调试不得并行",
            "逐任务审查与整票审查不得并行",
            "bounded entry = 一个已选 Ticket + 批准计划 + 按序执行",
            "每个任务使用 distinct fresh implementer",
            "完成所有任务后交还 Router",
            "不得从 bounded 直接进入 verification / branch finish",
        )
        for rule in expected_process_rules:
            with self.subTest(rule=rule):
                self.assertIn("".join(rule.split()), compact_guardrails_text)

        expected_debugging_rules = (
            "常规调试使用 systematic-debugging",
            "间歇性",
            "性能相关",
            "难复现",
            "常规 systematic-debugging 无法解决",
            "只有这些明确升级证据才使用 diagnosing-bugs",
            "普通调试与困难调试两个 loop 不同时运行",
        )
        for rule in expected_debugging_rules:
            with self.subTest(rule=rule):
                self.assertIn("".join(rule.split()), compact_guardrails_text)

        expected_review_rules = (
            "每个任务按新实现者→RED–GREEN–REFACTOR→规格审查→质量审查执行",
            "规格审查发现问题则修复并重复至 PASS，再进入质量审查",
            "质量审查发现问题则修复并重复至 PASS",
            "完成所有任务后进行整票 code-review",
        )
        for rule in expected_review_rules:
            with self.subTest(rule=rule):
                self.assertIn("".join(rule.split()), compact_guardrails_text)

        self.assertIn(
            "".join("自动路由只免除路由确认，不扩大权限".split()),
            compact_guardrails_text,
        )
        for gated_action in (
            "工作区/目录创建",
            "Git 初始化",
            "外部写入",
            "Issue Tracker",
            "worktree",
            "凭证",
            "破坏性操作",
            "commit",
            "push",
            "PR",
            "deploy/release",
            "外部通信",
        ):
            with self.subTest(gated_action=gated_action):
                self.assertIn("".join(gated_action.split()), compact_guardrails_text)
        self.assertIn("均保留独立授权门", compact_guardrails_text)

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
        for index in range(owners.count()):
            with self.subTest(stage=index + 1):
                owner = owners.nth(index)
                owner.scroll_into_view_if_needed()
                expect(owner).to_be_visible()
                owner_state = owner.evaluate(
                    """
                    element => {
                      const style = getComputedStyle(element);
                      const rect = element.getBoundingClientRect();
                      const centerX = rect.left + rect.width / 2;
                      const centerY = rect.top + rect.height / 2;
                      const hit = document.elementFromPoint(centerX, centerY);
                      return {
                        text: element.textContent.trim(),
                        visibility: style.visibility,
                        opacity: Number.parseFloat(style.opacity),
                        centerInViewport:
                          centerX >= 0
                          && centerX <= window.innerWidth
                          && centerY >= 0
                          && centerY <= window.innerHeight,
                        centerHitsOwner:
                          hit === element || (hit !== null && element.contains(hit)),
                      };
                    }
                    """
                )
                self.assertTrue(owner_state["text"])
                self.assertEqual(owner_state["visibility"], "visible")
                self.assertGreater(owner_state["opacity"], 0)
                self.assertTrue(owner_state["centerInViewport"])
                self.assertTrue(owner_state["centerHitsOwner"])

        for section_id in ("workflow", "ownership", "guardrails"):
            with self.subTest(section=section_id):
                section = page.locator(f"#{section_id}")
                self.assertEqual(section.count(), 1)
                self.assertTrue(section.is_visible())


if __name__ == "__main__":
    import unittest

    unittest.main()
