/* Purpose: Drive the Ask page. POST /api/ask, render one of three states:
 *          answer (text + citations), defer (red banner + verbatim passage),
 *          or noanswer (link to library).
 *
 * Unit:    nginx.service (static asset; proxies /api/ask to 127.0.0.1:8200)
 * Phase:   6
 */
(function () {
  "use strict";

  var ENDPOINT = "/api/ask";
  var TIMEOUT_MS = 25000;

  function $(sel) { return document.querySelector(sel); }
  function hide(el) { if (el) el.hidden = true; }
  function show(el) { if (el) el.hidden = false; }
  function setText(el, text) { if (el) el.textContent = text || ""; }

  function clearResults() {
    hide($("#ask-status"));
    hide($("#ask-defer"));
    hide($("#ask-answer"));
    hide($("#ask-noanswer"));
    hide($("#ask-error"));
  }

  function renderDefer(body) {
    var el = $("#ask-defer");
    setText(el.querySelector(".ask-defer__banner"), body.banner || "");
    setText(el.querySelector(".ask-defer__passage"), body.answer || "");
    var link = el.querySelector(".ask-defer__link");
    var first = (body.citations && body.citations[0]) || null;
    if (link && first && first.url) {
      link.setAttribute("href", first.url);
      link.textContent = "Open " + (first.article || "the source") + " →";
    } else if (link) {
      link.setAttribute("href", "/library/");
      link.textContent = "Open the library →";
    }
    show(el);
  }

  function renderAnswer(body) {
    var el = $("#ask-answer");
    setText(el.querySelector(".ask-answer__text"), body.answer || "");
    var list = el.querySelector(".ask-answer__cites");
    list.textContent = "";
    (body.citations || []).forEach(function (c) {
      var li = document.createElement("li");
      var a = document.createElement("a");
      a.setAttribute("href", c.url || "/library/");
      a.textContent = (c.article || "Source") + (c.section ? " — " + c.section : "");
      li.appendChild(a);
      list.appendChild(li);
    });
    show(el);
  }

  function renderNoAnswer() {
    show($("#ask-noanswer"));
  }

  function renderError() {
    show($("#ask-error"));
  }

  function submit(ev) {
    ev.preventDefault();
    var q = ($("#ask-q") || {}).value;
    if (!q || !q.trim()) return;
    clearResults();
    show($("#ask-status"));

    var ac = ("AbortController" in window) ? new AbortController() : null;
    var timeoutId = setTimeout(function () { if (ac) ac.abort(); }, TIMEOUT_MS);

    fetch(ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      cache: "no-store",
      body: JSON.stringify({ q: q }),
      signal: ac ? ac.signal : undefined
    })
      .then(function (r) {
        clearTimeout(timeoutId);
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (body) {
        hide($("#ask-status"));
        if (body && body.mode === "defer") return renderDefer(body);
        if (body && body.mode === "answer" && body.answer) return renderAnswer(body);
        return renderNoAnswer();
      })
      .catch(function () {
        hide($("#ask-status"));
        renderError();
      });
  }

  function init() {
    var form = $("#ask-form");
    if (form) form.addEventListener("submit", submit);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
