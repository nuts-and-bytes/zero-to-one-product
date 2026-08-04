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

    def test_mobile_navigation_remains_available_without_javascript(self):
        page = self.open_page(
            width=390,
            height=844,
            java_script_enabled=False,
        )

        scroll_width, client_width = page.evaluate(
            "[document.documentElement.scrollWidth, "
            "document.documentElement.clientWidth]"
        )
        self.assertLessEqual(scroll_width, client_width)

        navigation = page.get_by_role("navigation", name="主要导航")
        menu_button = page.locator("[data-menu-toggle]")
        self.assertTrue(navigation.is_visible())
        self.assertFalse(menu_button.is_visible())

        navigation_box = navigation.bounding_box()
        hero_box = page.locator(".hero-copy").bounding_box()
        self.assertIsNotNone(navigation_box)
        self.assertIsNotNone(hero_box)
        navigation_bottom = navigation_box["y"] + navigation_box["height"]
        self.assertLessEqual(
            navigation_bottom,
            hero_box["y"] + 1,
            f"navigation bottom {navigation_bottom}px overlaps "
            f"hero top {hero_box['y']}px",
        )

    def test_mobile_navigation_resets_when_viewport_becomes_desktop(self):
        page = self.open_page(width=390, height=844)

        menu_button = page.locator("[data-menu-toggle]")
        menu_button.click()
        self.assertEqual(menu_button.get_attribute("aria-expanded"), "true")

        page.set_viewport_size({"width": 1024, "height": 800})
        self.assertEqual(menu_button.get_attribute("aria-expanded"), "false")
        self.assertEqual(menu_button.get_attribute("aria-label"), "打开导航")

        page.set_viewport_size({"width": 390, "height": 844})
        self.assertFalse(
            page.get_by_role("navigation", name="主要导航").is_visible()
        )

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

        reveal_styles = page.locator("[data-reveal]").evaluate_all(
            "elements => elements.map(element => ({"
            "transitionDuration: getComputedStyle(element).transitionDuration, "
            "opacity: getComputedStyle(element).opacity, "
            "transform: getComputedStyle(element).transform"
            "}))"
        )
        self.assertGreater(len(reveal_styles), 0)
        for reveal_style in reveal_styles:
            self.assertIn(
                reveal_style["transitionDuration"],
                {"0s", "0.001s"},
            )
            self.assertEqual(reveal_style["opacity"], "1")
            self.assertEqual(reveal_style["transform"], "none")

    def test_number_labels_meet_wcag_text_contrast(self):
        page = self.open_page()

        contrast_samples = page.locator(
            ".principle-index, .route-number"
        ).evaluate_all(
            """
            elements => {
              const channels = color =>
                color.match(/[\\d.]+/g).slice(0, 3).map(Number);
              const luminance = color => {
                const values = channels(color).map(value => {
                  const normalized = value / 255;
                  return normalized <= 0.03928
                    ? normalized / 12.92
                    : ((normalized + 0.055) / 1.055) ** 2.4;
                });
                return 0.2126 * values[0]
                  + 0.7152 * values[1]
                  + 0.0722 * values[2];
              };
              const opaqueBackground = element => {
                let current = element;
                while (current) {
                  const color = getComputedStyle(current).backgroundColor;
                  const values = color.match(/[\\d.]+/g);
                  if (values && (values.length < 4 || Number(values[3]) > 0)) {
                    return color;
                  }
                  current = current.parentElement;
                }
                return "rgb(255, 255, 255)";
              };
              return elements.map(element => {
                const foreground = getComputedStyle(element).color;
                const background = opaqueBackground(element);
                const foregroundLuminance = luminance(foreground);
                const backgroundLuminance = luminance(background);
                const ratio = (Math.max(
                  foregroundLuminance,
                  backgroundLuminance
                ) + 0.05) / (Math.min(
                  foregroundLuminance,
                  backgroundLuminance
                ) + 0.05);
                return {
                  label: element.className,
                  foreground,
                  background,
                  ratio,
                };
              });
            }
            """
        )

        self.assertEqual(len(contrast_samples), 4)
        for sample in contrast_samples:
            self.assertGreaterEqual(
                sample["ratio"],
                4.5,
                f"{sample['label']} contrast: {sample}",
            )

    def test_page_does_not_expose_variant_controls(self):
        page = self.open_page()

        self.assertEqual(page.locator("[data-variant]").count(), 0)
        self.assertEqual(page.locator("#variant-prev").count(), 0)
        self.assertEqual(page.locator("#variant-next").count(), 0)


if __name__ == "__main__":
    import unittest

    unittest.main()
