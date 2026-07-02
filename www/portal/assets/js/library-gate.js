/*
 * library-gate.js — gracefully disable plain "Open library" links when the
 * offline library is down.
 *
 * Every "/library/" link reverse-proxies to kiwix-serve on :8080, which
 * stays inactive until a ZIM is installed (ConditionPathExistsGlob in
 * rpi-hub-kiwix.service). Without this gate, the "Open library" buttons on
 * the sub-pages navigate straight to a 502 Bad Gateway when the hub has no
 * content yet.
 *
 * The landing-page Core-resources TILES are gated separately by
 * index.html's probeGroup() (they carry data-probe-group="/library/"), so
 * we skip those here via :not([data-probe-group]) to avoid double work.
 *
 * Loaded on every page that has a JS-visible "/library/" link. CSP-safe
 * (script-src 'self', connect-src 'self'). Links inside <noscript> never
 * enter the DOM while scripting is enabled, so the no-JS fallback links are
 * left untouched.
 */
(function () {
  "use strict";

  function disableAll(links) {
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      a.setAttribute("aria-disabled", "true");
      a.setAttribute("tabindex", "-1");
      a.setAttribute("title", "Offline — no library content is installed on this hub yet");
      /* Keep the href so its target stays inspectable, but stop the click so
         the page never navigates to a dead 502 upstream. */
      a.addEventListener("click", function (e) { e.preventDefault(); }, false);
    }
  }

  function gate() {
    var links = document.querySelectorAll('a[href="/library/"]:not([data-probe-group])');
    if (!links.length) return;

    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, 5000) : null;

    fetch("/library/", {
      cache: "no-store",
      signal: controller ? controller.signal : undefined
    })
    .then(function (r) {
      if (timer) clearTimeout(timer);
      if (!r.ok) disableAll(links);
    })
    .catch(function () {
      if (timer) clearTimeout(timer);
      disableAll(links);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", gate);
  } else {
    gate();
  }
})();
