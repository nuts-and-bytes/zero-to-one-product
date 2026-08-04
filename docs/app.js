(function () {
  "use strict";

  document.documentElement.classList.add("js");

  var header = document.querySelector("[data-site-header]");
  var menuButton = document.querySelector("[data-menu-toggle]");
  var navigation = document.getElementById("primary-navigation");

  function setMenuOpen(isOpen) {
    if (!header || !menuButton) {
      return;
    }

    header.classList.toggle("is-open", isOpen);
    menuButton.setAttribute("aria-expanded", String(isOpen));
    menuButton.setAttribute("aria-label", isOpen ? "关闭导航" : "打开导航");
  }

  if (header && menuButton && navigation) {
    menuButton.addEventListener("click", function () {
      setMenuOpen(menuButton.getAttribute("aria-expanded") !== "true");
    });

    navigation.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener("click", function () {
        setMenuOpen(false);
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && menuButton.getAttribute("aria-expanded") === "true") {
        setMenuOpen(false);
        menuButton.focus();
      }
    });
  }

  var skipLink = document.querySelector(".skip-link");
  var mainContent = document.getElementById("main-content");

  if (skipLink && mainContent) {
    skipLink.addEventListener("click", function (event) {
      event.preventDefault();
      mainContent.focus();
      mainContent.scrollIntoView();
    });
  }

  var revealElements = Array.from(document.querySelectorAll("[data-reveal]"));
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function showImmediately() {
    revealElements.forEach(function (element) {
      element.classList.add("is-visible");
    });
  }

  if (reduceMotion || !("IntersectionObserver" in window)) {
    showImmediately();
    return;
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "0px 0px -8%", threshold: 0.12 }
  );

  revealElements.forEach(function (element) {
    observer.observe(element);
  });
})();
