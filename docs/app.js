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
        var targetId = decodeURIComponent(link.getAttribute("href").slice(1));
        var target = document.getElementById(targetId);
        if (target) {
          var hasExistingTabindex = target.hasAttribute("tabindex");
          if (!hasExistingTabindex) {
            target.setAttribute("tabindex", "-1");
            target.addEventListener(
              "blur",
              function removeTemporaryTabindex() {
                target.removeAttribute("tabindex");
              },
              { once: true }
            );
          }
          target.focus({ preventScroll: true });
        }
      });
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && menuButton.getAttribute("aria-expanded") === "true") {
        setMenuOpen(false);
        menuButton.focus();
      }
    });

    var desktopViewport = window.matchMedia("(min-width: 768px)");
    var closeMenuForDesktop = function (event) {
      if (event.matches) {
        setMenuOpen(false);
      }
    };

    if (typeof desktopViewport.addEventListener === "function") {
      desktopViewport.addEventListener("change", closeMenuForDesktop);
    } else {
      desktopViewport.addListener(closeMenuForDesktop);
    }

    document.documentElement.classList.add("menu-enhanced");
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

  var copyButtons = Array.from(document.querySelectorAll("button[data-copy-command]"));

  function copyWithSelection(codeElement) {
    if (!codeElement || typeof document.execCommand !== "function") {
      return false;
    }

    var selection = window.getSelection();
    if (!selection) {
      return false;
    }
    var savedRanges = [];
    for (var rangeIndex = 0; rangeIndex < selection.rangeCount; rangeIndex += 1) {
      savedRanges.push(selection.getRangeAt(rangeIndex).cloneRange());
    }
    var range = document.createRange();
    range.selectNodeContents(codeElement);

    try {
      selection.removeAllRanges();
      selection.addRange(range);
      try {
        return Boolean(document.execCommand("copy"));
      } catch (_error) {
        return false;
      }
    } finally {
      selection.removeAllRanges();
      savedRanges.forEach(function (savedRange) {
        selection.addRange(savedRange);
      });
    }
  }

  function copyCommand(command, codeElement) {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      return Promise.resolve()
        .then(function () {
          return navigator.clipboard.writeText(command);
        })
        .then(function () {
          return true;
        })
        .catch(function () {
          return copyWithSelection(codeElement);
        });
    }

    return Promise.resolve(copyWithSelection(codeElement));
  }

  copyButtons.forEach(function (button) {
    var block = button.closest("[data-command-block]");
    var codeElement = block && block.querySelector("code[data-command]");
    var status = block && block.querySelector("[data-copy-status][aria-live]");
    var label = button.querySelector("[data-copy-label]");
    var idleVisibleLabel = label ? label.textContent : button.textContent;
    var idleAccessibleLabel = button.getAttribute("aria-label");
    var idleStatus = status ? status.textContent : "";
    var resetTimer;
    var operationId = 0;

    button.addEventListener("click", function () {
      var command = button.dataset.copyCommand;
      operationId += 1;
      var currentOperationId = operationId;
      button.focus({ preventScroll: true });
      window.clearTimeout(resetTimer);

      copyCommand(command, codeElement).then(function (copied) {
        if (currentOperationId !== operationId) {
          return;
        }
        var feedback = copied ? "已复制" : "复制失败";
        block.dataset.copyState = copied ? "success" : "error";
        if (label) {
          label.textContent = feedback;
        }
        button.setAttribute(
          "aria-label",
          (idleAccessibleLabel || idleVisibleLabel) + "，" + feedback
        );
        if (status) {
          status.textContent = copied ? "已复制到剪贴板" : "复制失败，请手动选择命令";
        }

        resetTimer = window.setTimeout(function () {
          if (currentOperationId !== operationId) {
            return;
          }
          delete block.dataset.copyState;
          if (label) {
            label.textContent = idleVisibleLabel;
          }
          if (idleAccessibleLabel === null) {
            button.removeAttribute("aria-label");
          } else {
            button.setAttribute("aria-label", idleAccessibleLabel);
          }
          if (status) {
            status.textContent = idleStatus;
          }
        }, 1600);
      });
    });
  });

  var revealElements = Array.from(document.querySelectorAll("[data-reveal]"));
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function showImmediately() {
    revealElements.forEach(function (element) {
      element.classList.add("is-visible");
    });
  }

  if (reduceMotion || !("IntersectionObserver" in window)) {
    showImmediately();
  } else {
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
  }
})();
