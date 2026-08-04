from tests.site_test_support import SiteBrowserTestCase


class SiteFoundationAcceptanceTest(SiteBrowserTestCase):
    def test_homepage_presents_one_heading_and_the_core_facts(self):
        page = self.open_page()

        self.assertEqual(page.locator("h1").count(), 1)
        self.assertIn("有状态路由器", page.locator("main").inner_text())

        core_facts = page.get_by_test_id("core-facts").inner_text()
        self.assertIn("一个外层流程所有者", core_facts)
        self.assertIn("17 个精确依赖", core_facts)
        self.assertIn("每阶段一个主流程", core_facts)

    def test_workflow_sections_name_classification_and_scope_transfer_tools(self):
        page = self.open_page()

        classifier = page.locator("#classifier").inner_text()
        self.assertIn("grill-me", classifier)
        self.assertIn("grill-with-docs", classifier)
        self.assertIn("wayfinder", classifier)

        scope_transfer = page.locator("#scope-transfer").inner_text()
        self.assertIn("brainstorming", scope_transfer)
        self.assertIn("systematic-debugging", scope_transfer)
        self.assertIn("codebase-design", scope_transfer)

    def test_mobile_layout_has_no_horizontal_overflow_and_navigation_opens(self):
        page = self.open_page(width=390, height=844)

        scroll_width, client_width = page.evaluate(
            "[document.documentElement.scrollWidth, "
            "document.documentElement.clientWidth]"
        )
        self.assertLessEqual(scroll_width, client_width)

        navigation = page.get_by_role("navigation", name="主要导航")
        self.assertEqual(
            page.get_by_role("button", name="打开导航").count(),
            1,
        )
        menu_button = page.locator("[data-menu-toggle]")
        self.assertFalse(navigation.is_visible())
        self.assertEqual(menu_button.get_attribute("aria-expanded"), "false")

        menu_button.click()

        self.assertTrue(navigation.is_visible())
        self.assertEqual(menu_button.get_attribute("aria-expanded"), "true")

    def test_reduced_motion_preserves_skip_link_and_removes_reveal_animation(self):
        page = self.open_page(reduced_motion="reduce")

        self.assertEqual(page.locator("#main-content").count(), 1)
        page.keyboard.press("Tab")
        self.assertEqual(
            page.evaluate("document.activeElement.getAttribute('href')"),
            "#main-content",
        )
        page.keyboard.press("Enter")
        self.assertEqual(page.evaluate("document.activeElement.id"), "main-content")

        animation_durations = page.locator("[data-reveal]").evaluate_all(
            "elements => elements.map(element => "
            "getComputedStyle(element).animationDuration)"
        )
        self.assertGreater(len(animation_durations), 0)
        for animation_duration in animation_durations:
            self.assertIn(animation_duration, {"0s", "0.001s"})

    def test_page_does_not_expose_variant_controls(self):
        page = self.open_page()

        self.assertEqual(page.locator("[data-variant]").count(), 0)
        self.assertEqual(page.locator("#variant-prev").count(), 0)
        self.assertEqual(page.locator("#variant-next").count(), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
