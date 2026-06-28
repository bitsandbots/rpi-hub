/* Purpose: Drive board.html — fetch /api/notes, post new notes, surface
 *          rate-limit responses cleanly. Renders text verbatim (URLs
 *          visible but not linkified, per spec).
 *
 * Unit:    nginx.service (static asset; proxies /api/notes to 127.0.0.1:8400)
 * Phase:   9
 */
(function () {
  "use strict";

  var ENDPOINT = "/api/notes";
  var POLL_MS = 8000;

  function $(sel) { return document.querySelector(sel); }
  function escape(s) {
    if (s == null) return "";
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c];
    });
  }

  function fmtAge(ts) {
    var now = Date.now() / 1000;
    var dt = Math.max(0, now - ts);
    if (dt < 60) return "just now";
    if (dt < 3600) return Math.round(dt / 60) + "m ago";
    if (dt < 86400) return Math.round(dt / 3600) + "h ago";
    return Math.round(dt / 86400) + "d ago";
  }

  function render(notes) {
    var list = $("#board-notes");
    var empty = $("#board-empty");
    if (!list) return;
    list.textContent = "";
    if (!notes || !notes.length) {
      if (empty) empty.hidden = false;
      return;
    }
    if (empty) empty.hidden = true;
    notes.forEach(function (n) {
      var li = document.createElement("li");
      li.className = "board-note";
      // Render text verbatim. URLs are *not* turned into anchor tags.
      // That's the spec: URLs visible but not clickable.
      li.innerHTML =
        '<header class="board-note__h">'
        + '<span class="board-note__name">' + escape(n.name || "anonymous") + "</span>"
        + '<time class="board-note__age">' + escape(fmtAge(n.created_ts)) + "</time>"
        + "</header>"
        + '<p class="board-note__text"></p>';
      li.querySelector(".board-note__text").textContent = String(n.text || "");
      list.appendChild(li);
    });
  }

  function reload() {
    fetch(ENDPOINT + "?limit=100", { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (body) { render(body.notes || []); })
      .catch(function () { /* board offline — leave previous render */ });
  }

  function setStatus(msg, isError) {
    var el = $("#board-status");
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("svc-status--error", !!isError);
  }

  function submit(ev) {
    ev.preventDefault();
    var text = ($("#board-text") || {}).value || "";
    var name = ($("#board-name") || {}).value || "";
    if (!text.trim()) return;
    setStatus("Posting…", false);
    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ text: text, name: name })
    }).then(function (r) {
      if (r.status === 201) {
        setStatus("", false);
        $("#board-text").value = "";
        updateCounter();
        reload();
        return;
      }
      return r.json().then(function (body) {
        setStatus(body.detail || ("Could not post (HTTP " + r.status + ")"), true);
      });
    }).catch(function () {
      setStatus("The board isn't reachable right now.", true);
    });
  }

  function updateCounter() {
    var ta = $("#board-text");
    var counter = $("#board-counter");
    if (!ta || !counter) return;
    var remaining = 280 - (ta.value || "").length;
    counter.textContent = String(Math.max(0, remaining));
    counter.classList.toggle("board-counter--low", remaining <= 30);
  }

  function init() {
    var form = $("#board-form");
    if (form) form.addEventListener("submit", submit);
    var ta = $("#board-text");
    if (ta) ta.addEventListener("input", updateCounter);
    updateCounter();
    reload();
    setInterval(reload, POLL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
