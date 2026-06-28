/* Purpose: Drive sky.html — kick off a GPS acquisition sweep via
 *          POST /api/listen/gps/sweep and poll GET /api/listen/gps until
 *          the report lands. Renders acquired satellites first, then the
 *          strongest non-acquired rows for noise-floor context.
 *
 * Unit:    nginx.service (static asset; proxies /api/listen to 127.0.0.1:8300)
 * Phase:   13
 */
(function () {
  "use strict";

  var ENDPOINT = "/api/listen/gps";
  var POLL_MS = 2500;

  function $(s) { return document.querySelector(s); }

  var pollTimer = null;

  function bar(metric) {
    var width = 14;
    var filled = Math.max(0, Math.min(width, Math.round((metric / 20) * width)));
    var out = "";
    for (var i = 0; i < width; i++) out += i < filled ? "█" : "░";
    return out;
  }

  function fmtTs(ts) {
    if (!ts) return "—";
    try { return new Date(ts * 1000).toLocaleTimeString(); }
    catch (e) { return "—"; }
  }

  function setError(msg) {
    var el = $("#sky-error");
    if (!el) return;
    el.hidden = !msg;
    el.textContent = msg || "";
  }

  function renderReport(rec) {
    $("#sky-when").textContent = fmtTs(rec.completed_ts);
    if (!rec.ok) {
      $("#sky-count").textContent = "—";
      $("#sky-bias").textContent = "—";
      setError("Sweep failed: " + (rec.error || "unknown error"));
      $("#sky-results").textContent = "";
      return;
    }
    setError("");
    var rep = rec.report || {};
    var results = rep.results || [];
    $("#sky-count").textContent =
      (rep.acquired_count || 0) + " / " + results.length;
    $("#sky-bias").textContent = rep.bias_tee ? "ON" : "OFF";

    var acquired = results.filter(function (r) { return r.acquired; });
    var rest = results.filter(function (r) { return !r.acquired; }).slice(0, 5);

    var box = $("#sky-results");
    box.textContent = "";

    function row(r) {
      var div = document.createElement("div");
      div.className = "peer " + (r.acquired ? "peer--trusted" : "peer--unverified");
      var strong = document.createElement("strong");
      strong.textContent = "PRN " + r.prn + (r.acquired ? " — LOCKED" : " — not acquired");
      var meta = document.createElement("div");
      meta.className = "dataref";
      meta.textContent =
        "Doppler " + (r.doppler_hz >= 0 ? "+" : "") + r.doppler_hz + " Hz" +
        " · metric " + r.metric.toFixed(1) +
        " · " + bar(r.metric);
      div.appendChild(strong);
      div.appendChild(meta);
      return div;
    }

    if (acquired.length === 0) {
      var none = document.createElement("p");
      none.textContent =
        "No satellites acquired. Check: active GPS antenna connected, " +
        "bias tee ON, clear sky view. Strongest candidates below.";
      box.appendChild(none);
    }
    acquired.forEach(function (r) { box.appendChild(row(r)); });
    rest.forEach(function (r) { box.appendChild(row(r)); });
  }

  function refresh() {
    fetch(ENDPOINT, { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (st) {
        var hw = $("#sky-hwbanner");
        if (hw) {
          hw.hidden = !!st.dongle_present || !!st.simulate;
          hw.setAttribute("aria-hidden", hw.hidden ? "true" : "false");
        }
        $("#sky-status").textContent = st.running ? "sweeping…" : "idle";
        $("#sky-run").disabled = !!st.running;
        if (!st.running && pollTimer) {
          clearInterval(pollTimer);
          pollTimer = null;
        }
        if (st.last) renderReport(st.last);
      })
      .catch(function () { /* keep previous render */ });
  }

  function runSweep() {
    setError("");
    $("#sky-busybanner").hidden = true;
    fetch(ENDPOINT + "/sweep", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ integration_ms: 2 }),
    })
      .then(function (r) {
        if (r.status === 409) {
          $("#sky-busybanner").hidden = false;
          throw new Error("busy");
        }
        if (r.status === 503) {
          setError("No RTL-SDR dongle detected.");
          throw new Error("no hw");
        }
        if (!r.ok) throw new Error("HTTP " + r.status);
        $("#sky-status").textContent = "sweeping…";
        $("#sky-run").disabled = true;
        if (!pollTimer) pollTimer = setInterval(refresh, POLL_MS);
      })
      .catch(function () { /* banners already set */ });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = $("#sky-run");
    if (btn) btn.addEventListener("click", runSweep);
    refresh();
  });
})();
