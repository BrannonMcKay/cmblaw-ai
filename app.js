/* app.js — Interactive functionality for cmblaw.ai */
/* global Prism */

(function () {
  "use strict";

  /* ===== THEME TOGGLE ===== */
  function initTheme() {
    var toggle = document.querySelector(".theme-toggle");
    if (!toggle) return;

    toggle.addEventListener("click", function () {
      var html = document.documentElement;
      var current = html.getAttribute("data-theme");
      var next = current === "dark" ? "light" : "dark";
      html.setAttribute("data-theme", next);
      updateLogos(next);
    });
  }

  function updateLogos(theme) {
    var darkLogos = document.querySelectorAll(".logo-dark");
    var lightLogos = document.querySelectorAll(".logo-light");
    darkLogos.forEach(function (el) {
      el.style.display = theme === "dark" ? "" : "none";
    });
    lightLogos.forEach(function (el) {
      el.style.display = theme === "light" ? "" : "none";
    });
  }

  /* ===== MOBILE MENU ===== */
  function initMobileMenu() {
    var btn = document.querySelector(".mobile-menu-btn");
    var nav = document.querySelector(".mobile-nav");
    if (!btn || !nav) return;

    var openIcon = btn.querySelector(".menu-open");
    var closeIcon = btn.querySelector(".menu-close");

    btn.addEventListener("click", function () {
      var isOpen = nav.classList.toggle("open");
      if (openIcon) openIcon.style.display = isOpen ? "none" : "";
      if (closeIcon) closeIcon.style.display = isOpen ? "" : "none";
      btn.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });

    // Close on link click
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        nav.classList.remove("open");
        if (openIcon) openIcon.style.display = "";
        if (closeIcon) closeIcon.style.display = "none";
        btn.setAttribute("aria-expanded", "false");
      });
    });
  }

  /* ===== CODE TABS ===== */
  function initCodeTabs() {
    var codeBlocks = document.querySelectorAll(".code-block[data-endpoint]");

    codeBlocks.forEach(function (block) {
      var tabs = block.querySelectorAll(".code-block__tab");
      var contents = block.querySelectorAll(".code-block__content");

      tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
          var lang = tab.getAttribute("data-lang");
          if (!lang) return;

          // Update tabs
          tabs.forEach(function (t) { t.classList.remove("active"); });
          tab.classList.add("active");

          // Update content
          contents.forEach(function (c) {
            if (c.getAttribute("data-lang") === lang) {
              c.classList.add("active");
            } else {
              c.classList.remove("active");
            }
          });
        });
      });
    });
  }

  /* ===== COPY TO CLIPBOARD ===== */
  function initCopyButtons() {
    var buttons = document.querySelectorAll(".code-block__copy");

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var block = btn.closest(".code-block") || btn.closest(".response-block");
        if (!block) return;

        var activeContent = block.querySelector(".code-block__content.active, .response-block__content");
        if (!activeContent) return;

        var code = activeContent.querySelector("code");
        if (!code) return;

        var text = code.textContent;

        navigator.clipboard.writeText(text).then(function () {
          var originalHTML = btn.innerHTML;
          btn.innerHTML = '<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor"><path d="M13.78 4.22a.75.75 0 010 1.06l-7.25 7.25a.75.75 0 01-1.06 0L2.22 9.28a.75.75 0 011.06-1.06L6 10.94l6.72-6.72a.75.75 0 011.06 0z"/></svg> Copied!';
          btn.style.color = "var(--method-get)";

          setTimeout(function () {
            btn.innerHTML = originalHTML;
            btn.style.color = "";
          }, 2000);
        }).catch(function () {
          // Fallback: select text
          var range = document.createRange();
          range.selectNodeContents(code);
          var sel = window.getSelection();
          sel.removeAllRanges();
          sel.addRange(range);
        });
      });
    });
  }

  /* ===== SMOOTH SCROLL + ACTIVE NAV ===== */
  function initNavigation() {
    // Active link tracking
    var sections = document.querySelectorAll("section[id]");
    var navLinks = document.querySelectorAll(".header__nav-link, .mobile-nav a");

    function updateActiveLink() {
      var scrollPos = window.scrollY + 100;

      sections.forEach(function (section) {
        var top = section.offsetTop;
        var bottom = top + section.offsetHeight;
        var id = section.getAttribute("id");

        if (scrollPos >= top && scrollPos < bottom) {
          navLinks.forEach(function (link) {
            link.classList.remove("active");
            if (link.getAttribute("href") === "#" + id) {
              link.classList.add("active");
            }
          });
        }
      });
    }

    var scrollTimer;
    window.addEventListener("scroll", function () {
      if (scrollTimer) cancelAnimationFrame(scrollTimer);
      scrollTimer = requestAnimationFrame(updateActiveLink);
    }, { passive: true });

    updateActiveLink();
  }

  /* ===== SCROLL REVEAL ===== */
  function initScrollReveal() {
    var elements = document.querySelectorAll(".fade-in");
    if (!elements.length) return;

    // Add js-loaded class to enable fade-in styles
    document.body.classList.add("js-loaded");

    if ("IntersectionObserver" in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      }, {
        threshold: 0.05,
        rootMargin: "50px 0px 0px 0px"
      });

      elements.forEach(function (el) { observer.observe(el); });
    } else {
      elements.forEach(function (el) { el.classList.add("visible"); });
    }

    // Safety fallback: reveal all after 1 second
    setTimeout(function () {
      elements.forEach(function (el) { el.classList.add("visible"); });
    }, 1000);
  }

  /* ===== HEADER SHRINK ===== */
  function initHeaderScroll() {
    var header = document.querySelector(".header");
    if (!header) return;

    var scrolled = false;
    window.addEventListener("scroll", function () {
      var shouldShrink = window.scrollY > 20;
      if (shouldShrink !== scrolled) {
        scrolled = shouldShrink;
        if (scrolled) {
          header.style.boxShadow = "var(--shadow-md)";
        } else {
          header.style.boxShadow = "none";
        }
      }
    }, { passive: true });
  }

  /* ===== RE-HIGHLIGHT AFTER PRISM LOADS ===== */
  function initPrismRehighlight() {
    // Prism is loaded with defer, wait for it
    function highlight() {
      if (typeof Prism !== "undefined") {
        Prism.highlightAll();
      } else {
        setTimeout(highlight, 100);
      }
    }
    highlight();
  }

  /* ===== INIT ===== */
  function init() {
    initTheme();
    initMobileMenu();
    initCodeTabs();
    initCopyButtons();
    initNavigation();
    initScrollReveal();
    initHeaderScroll();
    initPrismRehighlight();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

})();
