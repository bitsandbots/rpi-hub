/* Purpose: Render the ADS-B aircraft list from dump1090's
 *          aircraft.json. dump1090-mutability writes this file every
 *          second to /run/dump1090-mutability/; nginx serves it at
 *          /adsb/aircraft.json so we don't have to proxy through
 *          signal-listen.
 *
 * Unit:    nginx.service (static asset; alias to dump1090 output dir)
 * Phase:   8.4
 */
(function () {
  "use strict";

  var ENDPOINT = "/adsb/aircraft.json";
  var POLL_MS = 3000;

  function $(s) { return document.querySelector(s); }

  function fmtAlt(a) {
    if (a == null) return "—";
    if (typeof a !== "number") return "—";
    return a.toLocaleString() + " ft";
  }
  function fmtSpd(s) {
    if (typeof s !== "number") return "—";
    return Math.round(s) + " kt";
  }
  function fmtTrk(t) {
    if (typeof t !== "number") return "—";
    return Math.round(t) + "°";
  }
  function fmtSeen(s) {
    if (typeof s !== "number") return "—";
    return s.toFixed(1) + "s ago";
  }

  function render(body) {
    var rows = $("#adsb-rows");
    var status = $("#adsb-status");
    if (!rows) return;
    var ac = (body && body.aircraft) || [];
    if (!ac.length) {
      if (status) status.textContent = "No aircraft in range right now.";
      rows.textContent = "";
      return;
    }
    if (status) status.textContent = ac.length + " aircraft visible";
    rows.textContent = "";
    ac.forEach(function (a) {
      var tr = document.createElement("tr");
      tr.innerHTML =
        '<td class="mono">' + (a.hex || "—") + '</td>'
        + '<td>' + (a.flight ? a.flight.trim() : "—") + '</td>'
        + '<td>' + fmtAlt(a.altitude) + '</td>'
        + '<td>' + fmtSpd(a.speed) + '</td>'
        + '<td>' + fmtTrk(a.track) + '</td>'
        + '<td>' + fmtSeen(a.seen) + '</td>';
      rows.appendChild(tr);
    });
  }

  function tick() {
    fetch(ENDPOINT, { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () {
        var status = $("#adsb-status");
        if (status) status.textContent = "dump1090 isn't running yet (ADS-B is sub-phase 8.4 polish).";
      });
  }

  function init() {
    tick();
    setInterval(tick, POLL_MS);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
