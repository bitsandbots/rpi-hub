/* Purpose: Drive peers.html — fetch /api/mesh/identity + /api/mesh/peers,
 *          render the peer list, surface the owner-scan workflow. The
 *          "trust" action requires the owner token; we deliberately do
 *          not show that input here — owner-marked trust is set from the
 *          device shell so a casual passer-by cannot promote a peer.
 *
 * Unit:    nginx.service (static asset; proxies /api/mesh to 127.0.0.1:8500)
 * Phase:   7
 */
(function () {
  "use strict";

  var ENDPOINT = "/api/mesh";

  function $(s) { return document.querySelector(s); }
  function escape(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtAge(ts) {
    var dt = Math.max(0, Date.now() / 1000 - ts);
    if (dt < 60) return "just now";
    if (dt < 3600) return Math.round(dt / 60) + "m ago";
    if (dt < 86400) return Math.round(dt / 3600) + "h ago";
    return Math.round(dt / 86400) + "d ago";
  }

  function refreshIdentity() {
    fetch(ENDPOINT + "/identity", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (body) {
        var fp = $("#peers-fp");
        if (fp) fp.textContent = body.fingerprint || "—";
      })
      .catch(function () { /* leave dash */ });
  }

  function refreshPeers() {
    fetch(ENDPOINT + "/peers", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (body) {
        var rows = $("#peers-rows");
        var empty = $("#peers-empty");
        if (!rows) return;
        var list = body.peers || [];
        rows.textContent = "";
        if (!list.length) { if (empty) empty.hidden = false; return; }
        if (empty) empty.hidden = true;
        list.forEach(function (p) {
          var li = document.createElement("li");
          li.className = "peer peer--" + p.trust;
          li.innerHTML =
            '<div class="peer__h">'
            + '<strong>' + escape(p.display_name || p.fingerprint) + '</strong>'
            + ' <span class="peer__trust">' + escape(p.trust) + '</span>'
            + '</div>'
            + '<div class="peer__meta">'
            + 'Fingerprint: <code>' + escape(p.fingerprint) + '</code>'
            + ' · Radio: ' + escape(p.radio)
            + (p.last_rssi != null ? ' · RSSI ' + escape(p.last_rssi) + ' dBm' : '')
            + ' · Last seen ' + escape(fmtAge(p.last_seen_ts))
            + '</div>'
            + (p.trust === "unverified"
                ? '<p class="peer__banner">Unverified peer — owner has not marked this node as trusted.</p>'
                : '');
          rows.appendChild(li);
        });
      })
      .catch(function () { /* leave previous render */ });
  }

  function init() {
    refreshIdentity();
    refreshPeers();
    setInterval(refreshPeers, 10000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
