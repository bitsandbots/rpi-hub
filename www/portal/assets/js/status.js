/* Purpose: Fetch /api/status (Phase 5) and render metrics on status.html.
 *          Phase 4 ships this client ahead of the API. When the API isn't
 *          running yet — fresh image, Phase 5 not installed, or unit
 *          stopped — we show a calm explanatory banner instead of a wall
 *          of "—". Polls every 5s while the tab is visible; pauses on
 *          hidden tabs to keep the Pi cool.
 *
 * Unit:    nginx.service (static asset; proxies /api/status to 127.0.0.1:8000)
 * Phase:   4 (UI), with a forward dependency on Phase 5 (signal-status)
 */
(function () {
  "use strict";

  var POLL_MS = 5000;
  var ENDPOINT = "/api/status";
  var timer = null;

  function $(sel) { return document.querySelector(sel); }

  function fmtUptime(seconds) {
    if (typeof seconds !== "number" || !isFinite(seconds) || seconds < 0) return "—";
    var d = Math.floor(seconds / 86400);
    var h = Math.floor((seconds % 86400) / 3600);
    var m = Math.floor((seconds % 3600) / 60);
    if (d > 0) return d + "d " + h + "h " + m + "m";
    if (h > 0) return h + "h " + m + "m";
    return m + "m";
  }

  function fmtBytes(n) {
    if (typeof n !== "number" || !isFinite(n) || n < 0) return "—";
    var units = ["B", "KB", "MB", "GB", "TB"];
    var i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
    return (n >= 100 ? n.toFixed(0) : n.toFixed(1)) + " " + units[i];
  }

  function fmtStorage(s) {
    if (!s) return { value: "—", hint: "" };
    var free = s.kiwix_bytes_free;
    var total = s.kiwix_bytes_total;
    var hint = "";
    if (typeof free === "number" && typeof total === "number" && total > 0) {
      var pct = Math.round((free / total) * 100);
      hint = pct + "% free of " + fmtBytes(total);
    }
    return { value: fmtBytes(free), hint: hint };
  }

  function voltageState(v) {
    // Returns { value, hint, severity }. severity ∈ { "ok", "warn", "bad" }.
    if (!v) return { value: "—", hint: "", severity: "ok" };
    if (v.undervoltage === true) {
      return { value: "Undervoltage", hint: "Check power supply / cable", severity: "bad" };
    }
    if (v.throttled && v.throttled !== "0x0" && v.throttled !== 0) {
      return { value: "Throttling", hint: "Code " + v.throttled, severity: "warn" };
    }
    return { value: "Nominal", hint: v.throttled ? ("Code " + v.throttled) : "", severity: "ok" };
  }

  function setMetric(card, value, hint, severity) {
    if (!card) return;
    var v = card.querySelector(".metric__value");
    var h = card.querySelector(".metric__hint");
    if (v) v.textContent = value == null ? "—" : String(value);
    if (h) h.textContent = hint || "";
    card.classList.remove("metric--warn", "metric--bad");
    if (severity === "warn") card.classList.add("metric--warn");
    if (severity === "bad")  card.classList.add("metric--bad");
  }

  function renderUnavailable(reason) {
    setMetric($("#m-uptime"),  "—", "Waiting for status service");
    setMetric($("#m-storage"), "—", "Waiting for status service");
    setMetric($("#m-voltage"), "—", "Waiting for status service");
    setMetric($("#m-clients"), "—", "Waiting for status service");
    var banner = $("#api-banner");
    if (banner) {
      banner.classList.remove("hidden");
      var msg = banner.querySelector(".api-banner__msg");
      if (msg) msg.textContent = reason || "The status service isn't running yet.";
    }
    var stamp = $("#m-stamp");
    if (stamp) stamp.textContent = "Status service unreachable";
  }

  function renderServices(svc) {
    if (!svc) return;
    var rows = document.querySelectorAll("#services-list li");
    rows.forEach(function (li) {
      var key = li.getAttribute("data-svc");
      var state = svc[key] || "unknown";
      var stateEl = li.querySelector(".services-list__state");
      var dotEl = li.querySelector(".services-list__dot");
      if (stateEl) stateEl.textContent = state;
      li.classList.remove(
        "services-list__row--ready",
        "services-list__row--off",
        "services-list__row--unknown"
      );
      if (state === "ready") li.classList.add("services-list__row--ready");
      else if (state === "not-running") li.classList.add("services-list__row--off");
      else li.classList.add("services-list__row--unknown");
      if (dotEl) { /* dot color is driven by row class via CSS */ }
    });
    var fp = svc.mesh_fingerprint;
    var fpRow = $("#services-fp");
    if (fpRow) {
      if (fp) {
        var code = fpRow.querySelector("code");
        if (code) code.textContent = fp;
        fpRow.hidden = false;
      } else {
        fpRow.hidden = true;
      }
    }
  }

  function renderData(data) {
    var banner = $("#api-banner");
    if (banner) banner.classList.add("hidden");

    setMetric($("#m-uptime"), fmtUptime(data.uptime_seconds), data.load_avg ? ("Load " + data.load_avg.join(" / ")) : "");

    var st = fmtStorage(data.storage);
    setMetric($("#m-storage"), st.value, st.hint);

    var v = voltageState(data.voltage);
    setMetric($("#m-voltage"), v.value, v.hint, v.severity);

    var clients = (typeof data.dhcp_clients === "number") ? data.dhcp_clients : "—";
    setMetric($("#m-clients"), clients, clients === 0 ? "Just you (hub itself)" : "");

    renderServices(data.services);

    var stamp = $("#m-stamp");
    if (stamp) {
      var now = new Date();
      stamp.textContent = "Updated " + now.toLocaleTimeString();
    }
  }

  function tick() {
    var ac = ("AbortController" in window) ? new AbortController() : null;
    var timeoutId = setTimeout(function () { if (ac) ac.abort(); }, 4000);
    fetch(ENDPOINT, { signal: ac ? ac.signal : undefined, headers: { "Accept": "application/json" }, cache: "no-store" })
      .then(function (r) {
        clearTimeout(timeoutId);
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(renderData)
      .catch(function (e) {
        renderUnavailable(
          e && e.name === "AbortError"
            ? "The status service is taking too long to respond."
            : "The status service isn't running yet — Phase 5 adds it."
        );
      });
  }

  function start() {
    stop();
    tick();
    timer = setInterval(tick, POLL_MS);
  }
  function stop() {
    if (timer != null) { clearInterval(timer); timer = null; }
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) stop(); else start();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
