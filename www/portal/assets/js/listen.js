/* Purpose: Drive listen.html — pick a mode, load presets, send /tune
 *          and /stop, poll /alerts for any active NOAA alerts. No
 *          WebSocket audio in this commit; the audio bridge lands in
 *          a follow-up (sub-phase 8.3 polish) once we have a Pi 4 + dongle
 *          on the bench to tune timing parameters against.
 *
 * Unit:    nginx.service (static asset; proxies /api/listen to 127.0.0.1:8300)
 * Phase:   8
 */
(function () {
  "use strict";

  var ENDPOINT = "/api/listen";

  function $(s) { return document.querySelector(s); }
  function hide(el) { if (el) el.hidden = true; }
  function show(el) { if (el) el.hidden = false; }

  var currentMode = null;

  function fmtFreq(hz) {
    if (typeof hz !== "number" || hz <= 0) return "—";
    return (hz / 1e6).toFixed(3) + " MHz";
  }

  function setHwBanner(visible) {
    var hw = $("#listen-hwbanner");
    if (!hw) return;
    hw.hidden = !visible;
    hw.setAttribute("aria-hidden", visible ? "false" : "true");
  }

  function refreshState() {
    fetch(ENDPOINT + "/state", { cache: "no-store" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (state) {
        var modeEl = $("#listen-mode");
        var freqEl = $("#listen-freq");
        var labelEl = $("#listen-label");
        if (modeEl) modeEl.textContent = state.mode || "idle";
        if (freqEl) freqEl.textContent = fmtFreq(state.frequency_hz);
        if (labelEl) labelEl.textContent = state.label || "—";
        setHwBanner(!state.dongle_present);
      })
      .catch(function () { /* leave previous render */ });
  }

  function loadPresets(mode) {
    var sel = $("#listen-preset");
    var tune = $("#listen-tune");
    if (!sel) return;
    sel.disabled = true;
    if (tune) tune.disabled = true;
    if (mode === "stop") {
      sel.textContent = "";
      return;
    }
    fetch(ENDPOINT + "/presets?mode=" + encodeURIComponent(mode), { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (body) {
        sel.textContent = "";
        (body.presets || []).forEach(function (p) {
          var opt = document.createElement("option");
          opt.value = String(p.frequency_hz);
          opt.textContent = p.label + " — " + fmtFreq(p.frequency_hz);
          opt.dataset.label = p.label;
          sel.appendChild(opt);
        });
        if (sel.options.length > 0) {
          sel.disabled = false;
          if (tune) tune.disabled = false;
        }
      })
      .catch(function () { /* presets fail soft */ });
  }

  function onModeClick(ev) {
    var mode = ev.currentTarget.getAttribute("data-mode");
    if (!mode) return;
    if (mode === "stop") {
      fetch(ENDPOINT + "/stop", { method: "POST", cache: "no-store" })
        .then(refreshState).catch(refreshState);
      return;
    }
    currentMode = mode;
    loadPresets(mode);
  }

  function onTune() {
    var sel = $("#listen-preset");
    if (!sel || sel.selectedIndex < 0 || !currentMode) return;
    var opt = sel.options[sel.selectedIndex];
    var freq = parseInt(opt.value, 10);
    var label = opt.dataset.label || "";
    fetch(ENDPOINT + "/tune", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ mode: currentMode, frequency_hz: freq, label: label })
    }).then(refreshState).catch(refreshState);
  }

  function refreshAlerts() {
    fetch(ENDPOINT + "/alerts", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (body) {
        var banner = $("#listen-banner");
        var msg = $("#listen-banner-text");
        if (!banner || !msg) return;
        var active = (body.alerts || []).find(function (a) { return a.promote_banner; });
        if (!active) { hide(banner); return; }
        msg.textContent =
          active.event_label + " — " + active.station + " (" + active.duration_minutes + " min)";
        show(banner);
      })
      .catch(function () { /* leave previous */ });
  }

  function init() {
    var btns = document.querySelectorAll(".listen-mode-btn");
    btns.forEach(function (b) { b.addEventListener("click", onModeClick); });
    var tune = $("#listen-tune");
    if (tune) tune.addEventListener("click", onTune);
    refreshState();
    refreshAlerts();
    setInterval(refreshState, 5000);
    setInterval(refreshAlerts, 15000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
