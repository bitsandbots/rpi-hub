/* Purpose: High-contrast theme toggle. Two responsibilities:
 *            1. Mark <html> with class="js" early so the toggle button is
 *               visible (CSS hides it without JS — never want a no-op button).
 *            2. Wire the .contrast-toggle button to flip a .contrast-high
 *               class on <html>, persisted in localStorage. Respects the
 *               OS-level prefers-contrast: more on first load.
 *
 *          Kept deliberately script-tag-includable from <head> with no
 *          DOMContentLoaded wait so the .js class lands before paint and
 *          the page doesn't flash an irrelevant toggle.
 *
 * Unit:    nginx.service (static asset)
 * Phase:   4
 */
(function () {
  "use strict";
  var KEY = "rpi-pod-contrast";
  var html = document.documentElement;
  html.classList.add("js");

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (_e) { /* private mode */ }

  var prefersMore =
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-contrast: more)").matches;

  var on = saved === "on" || (saved === null && prefersMore);
  if (on) html.classList.add("contrast-high");

  // Wire up after the toggle exists.
  function init() {
    var btn = document.querySelector(".contrast-toggle");
    if (!btn) return;
    function syncLabel() {
      var active = html.classList.contains("contrast-high");
      btn.setAttribute("aria-pressed", active ? "true" : "false");
      btn.textContent = active ? "High contrast: on" : "High contrast: off";
    }
    syncLabel();
    btn.addEventListener("click", function () {
      var active = html.classList.toggle("contrast-high");
      try { localStorage.setItem(KEY, active ? "on" : "off"); } catch (_e) {}
      syncLabel();
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
