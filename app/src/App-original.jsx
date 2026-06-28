import { useState, useEffect, useCallback, useRef } from "react";

/* ═══════════════════════════════════════════════════════════════
   rpi-hub Mobile App Interface
   Deploy to: www/portal/app.html (or replace index.html)
   When served from 192.168.4.1 / hub.local, app auto-connects.
   Otherwise defaults to demo mode with mock data.
═══════════════════════════════════════════════════════════════ */

const DEFAULT_POD = "http://192.168.4.1";

/* ─── MOCK DATA ───────────────────────────────────────────────── */
const MOCK = {
  status: {
    uptime_seconds: 86741,
    load_avg: [0.18, 0.12, 0.09],
    storage: { kiwix_bytes_free: 18_600_000_000, kiwix_bytes_total: 64_000_000_000 },
    voltage: { throttled: "0x0", undervoltage: false },
    dhcp_clients: 4,
    time_source: "rtc",
    build_version: "v1.2.1",
    services: {
      retrieve: "ready", assist: "not-running", listen: "ready",
      notes: "ready", mesh: "ready", adsb: "not-running",
      adsb_aircraft: 0, mesh_fingerprint: "A3F7-92BC-E15D-40F8"
    }
  },
  notes: [
    { id: "n1", text: "Water distribution at the community center — open until 6 PM.", ts: Date.now() - 3200000 },
    { id: "n2", text: "Oak Ave bridge is passable. No flooding reported.", ts: Date.now() - 7100000 },
    { id: "n3", text: "Mobile charging station active at Fire Station 12 on Main St.", ts: Date.now() - 10800000 },
    { id: "n4", text: "Medical volunteers at Eastside Church. Open to all.", ts: Date.now() - 18000000 },
  ],
  retrieve: [
    { article: "Water purification", section: "Boiling methods", score: 0.94, url: "/library/A/Water_purification" },
    { article: "Water purification", section: "Chemical treatment", score: 0.87, url: "/library/A/Water_purification" },
    { article: "Emergency management", section: "Water supply", score: 0.73, url: "/library/A/Emergency_management" },
    { article: "Wilderness survival", section: "Finding water", score: 0.68, url: "/library/A/Wilderness_survival" },
  ],
  ask: {
    mode: "answer",
    answer: "To purify water in an emergency:\n1. Boil vigorously for 1 minute (3 min above 6,500 ft elevation).\n2. If boiling is not possible, use 2 drops of unscented bleach (6%) per liter and wait 30 min.\n3. Iodine or chlorine tablets work at standard dosage; follow package directions.\n4. Always filter visibly cloudy water through cloth before any treatment.",
    citations: [
      { number: 1, article: "Water purification", section: "Boiling", url: "/library/A/Water_purification" },
      { number: 2, article: "Water purification", section: "Chemical treatment", url: "/library/A/Water_purification" }
    ],
    confidence: 0.91
  },
  presets: [
    { label: "NOAA WX1", freq_mhz: 162.400, mode: "NFM" },
    { label: "NOAA WX2", freq_mhz: 162.425, mode: "NFM" },
    { label: "NOAA WX3", freq_mhz: 162.450, mode: "NFM" },
    { label: "NOAA WX4", freq_mhz: 162.475, mode: "NFM" },
    { label: "FM 91.5", freq_mhz: 91.5, mode: "WFM" },
    { label: "AM 1620", freq_mhz: 1.620, mode: "AM" },
  ],
  alerts: [
    { type: "NOAA SAME", event: "Winter Storm Watch", area: "Inland Empire / San Bernardino Mtns", ts: Date.now() - 2400000 }
  ],
  peers: [
    { id: "p1", fingerprint: "B2E8-71AC-D34F-89F1", trust: "TRUSTED", last_seen: Date.now() - 118000 },
    { id: "p2", fingerprint: "C9F1-83BD-E56G-90H2", trust: "UNVERIFIED", last_seen: Date.now() - 840000 },
  ]
};

/* ─── UTILITIES ──────────────────────────────────────────────── */
const fmtUptime = (s) => {
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m ${Math.floor(s % 60)}s`;
};
const fmtBytes = (b) => b > 1e9 ? `${(b/1e9).toFixed(1)} GB` : b > 1e6 ? `${(b/1e6).toFixed(0)} MB` : `${Math.round(b/1e3)} KB`;
const fmtAgo = (ts) => {
  const d = Date.now() - ts;
  if (d < 60000) return "just now";
  if (d < 3600000) return `${Math.floor(d/60000)}m ago`;
  if (d < 86400000) return `${Math.floor(d/3600000)}h ago`;
  return `${Math.floor(d/86400000)}d ago`;
};
const svcColor = (s) => ({ ready: "#4ade80", "not-running": "#2d3f2d", unknown: "#fbbf24" }[s] || "#fbbf24");

/* ─── ICONS (Feather-style SVG) ──────────────────────────────── */
const PATHS = {
  home: "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10",
  search: "M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z",
  chat: "M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z",
  radio: "M2.5 19h19M9 8a3 3 0 016 0v7H9V8zM12 3v1",
  clipboard: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
  settings: "M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06-.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z",
  x: "M18 6L6 18M6 6l12 12",
  send: "M22 2L11 13M22 2L15 22l-4-9-9-4z",
  alert: "M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01",
  wifi: "M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01",
  antenna: "M2 12a10 10 0 0020 0M5 12a7 7 0 0014 0M8 12a4 4 0 018 0M12 12v8M12 4v2",
};
const Ic = ({ name, size = 20, color = "currentColor" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    {(PATHS[name] || "").split("M").filter(Boolean).map((d, i) => (
      <path key={i} d={"M" + d} />
    ))}
  </svg>
);

/* ─── CSS ────────────────────────────────────────────────────── */
const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow+Condensed:wght@400;500;600;700&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#070c07;--sf:#0c140c;--el:#121d12;--bd:#1c2d1c;
  --gn:#4ade80;--gd:#14532d;--am:#fbbf24;--rd:#f87171;--bl:#60a5fa;
  --tx:#deeede;--mu:#5a7a5a;
  --mono:'Share Tech Mono','Courier New',monospace;
  --ui:'Barlow Condensed',sans-serif;
}
body{background:var(--bg);color:var(--tx);font-family:var(--mono);overflow:hidden}
#root{display:flex;flex-direction:column;height:100dvh;max-width:480px;margin:0 auto}

/* Header */
.hdr{background:var(--sf);border-bottom:1px solid var(--bd);padding:10px 14px;display:flex;align-items:center;gap:10px;flex-shrink:0;position:relative}
.hdr::after{content:'';position:absolute;bottom:-1px;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent 0%,var(--gn) 50%,transparent 100%);opacity:.3}
.logo{font-family:var(--ui);font-weight:700;font-size:20px;letter-spacing:4px;color:var(--gn);text-transform:uppercase;line-height:1}
.logo-sub{font-size:10px;color:var(--mu);font-weight:500;letter-spacing:2px;margin-top:1px}
.sig-bars{display:flex;align-items:flex-end;gap:2.5px;height:16px}
.sig-bar{width:3px;background:var(--bd);border-radius:1px;transition:background .3s}
.sig-bar.on{background:var(--gn);box-shadow:0 0 4px var(--gn)}
.sig-bar:nth-child(1){height:4px}.sig-bar:nth-child(2){height:7px}.sig-bar:nth-child(3){height:10px}.sig-bar:nth-child(4){height:14px}
.conn-lbl{font-size:10px;letter-spacing:1.5px;text-transform:uppercase;font-family:var(--ui);font-weight:700}
.conn-lbl.demo{color:var(--am)}.conn-lbl.online{color:var(--gn)}.conn-lbl.offline{color:var(--rd)}.conn-lbl.connecting{color:var(--bl)}
.btn-ic{background:none;border:none;color:var(--mu);cursor:pointer;padding:5px;border-radius:3px;display:flex;align-items:center;justify-content:center;transition:color .15s}
.btn-ic:hover{color:var(--tx)}

/* Demo banner */
.demo-baner{background:#3d1f00;border-bottom:1px solid #7c3a00;color:var(--am);font-size:11px;font-family:var(--ui);font-weight:600;letter-spacing:1px;text-align:center;padding:6px 14px;display:flex;align-items:center;justify-content:center;gap:7px;flex-shrink:0}

/* Main scroll */
.main{flex:1;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.main::-webkit-scrollbar{display:none}

/* Bottom nav */
.bnav{background:var(--sf);border-top:1px solid var(--bd);display:flex;flex-shrink:0;padding-bottom:env(safe-area-inset-bottom,0px)}
.nb{flex:1;background:none;border:none;cursor:pointer;padding:9px 0 7px;display:flex;flex-direction:column;align-items:center;gap:3px;font-family:var(--ui);font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:var(--mu);transition:color .15s}
.nb.act{color:var(--gn)}.nb:hover:not(.act){color:var(--tx)}

/* Screen */
.scr{padding:14px 14px;animation:fadeIn .12s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:translateY(0)}}

/* Sec header */
.sh{font-family:var(--ui);font-size:11px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--mu);margin-bottom:8px;display:flex;align-items:center;gap:8px}
.sh::after{content:'';flex:1;height:1px;background:var(--bd)}

/* Stat grid */
.sg{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
.st{background:var(--sf);border:1px solid var(--bd);padding:12px;position:relative;overflow:hidden}
.st::before{content:'';position:absolute;top:0;left:0;width:2px;height:100%;background:var(--gn);opacity:.5}
.sl{font-size:10px;color:var(--mu);letter-spacing:1.5px;text-transform:uppercase;font-family:var(--ui);font-weight:700;margin-bottom:3px}
.sv{font-size:20px;color:var(--gn);line-height:1;font-family:var(--mono)}
.ss{font-size:10px;color:var(--mu);margin-top:3px}

/* Services */
.svc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:10px}
.svc{background:var(--el);border:1px solid var(--bd);padding:10px 6px;display:flex;flex-direction:column;align-items:center;gap:5px;position:relative}
.svc-dot{width:7px;height:7px;border-radius:50%;position:absolute;top:5px;right:5px}
.svc-n{font-family:var(--ui);font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;text-align:center}
.svc-s{font-size:9px;color:var(--mu);text-transform:uppercase;font-family:var(--ui);letter-spacing:.5px}

/* Card */
.card{background:var(--sf);border:1px solid var(--bd);padding:12px 14px;margin-bottom:8px}

/* Progress */
.pbar{height:3px;background:var(--bd);margin-top:6px}
.pbar-fill{height:100%;background:linear-gradient(90deg,var(--gn),var(--bl));transition:width .4s}

/* Ask */
.ask-wrap{display:flex;flex-direction:column;height:100%}
.ask-hist{flex:1;overflow-y:auto;padding:14px;scrollbar-width:none}
.ask-hist::-webkit-scrollbar{display:none}
.ask-bar{border-top:1px solid var(--bd);padding:10px 14px;background:var(--bg);flex-shrink:0}
.ask-row{display:flex;gap:8px}
.ask-ta{flex:1;background:var(--sf);border:1px solid var(--bd);color:var(--tx);font-family:var(--mono);font-size:14px;padding:10px 12px;resize:none;outline:none;min-height:44px;max-height:100px;line-height:1.4;transition:border-color .15s}
.ask-ta:focus{border-color:var(--gn)}
.ask-ta::placeholder{color:var(--mu)}
.btn-send{background:var(--gd);border:1px solid var(--gn);color:var(--gn);cursor:pointer;width:44px;height:44px;display:flex;align-items:center;justify-content:center;transition:background .15s;flex-shrink:0}
.btn-send:hover:not(:disabled){background:#166534}
.btn-send:disabled{opacity:.35;cursor:default}

/* Msg bubbles */
.msg-q{text-align:right;margin-bottom:12px}
.msg-q-text{display:inline-block;background:var(--el);border:1px solid var(--bd);padding:8px 12px;font-size:13px;max-width:80%;text-align:left;color:var(--tx)}
.msg-a{margin-bottom:14px}
.mode-badge{display:inline-flex;align-items:center;gap:4px;font-family:var(--ui);font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;padding:2px 8px;margin-bottom:8px}
.mode-badge.answer{background:var(--gd);color:var(--gn)}
.mode-badge.defer{background:#7c2d12;color:#fb923c}
.mode-badge.noanswer,.mode-badge.error{background:var(--el);color:var(--mu)}
.conf{font-size:10px;color:var(--mu);margin-bottom:6px;font-family:var(--ui);letter-spacing:1px}
.ans-text{font-size:13px;line-height:1.65;color:var(--tx);white-space:pre-wrap}
.cites{margin-top:8px;border-top:1px solid var(--bd);padding-top:8px;display:flex;flex-direction:column;gap:3px}
.cite-row{font-size:11px;color:var(--bl);display:flex;gap:6px}
.cite-n{color:var(--mu)}

/* Search */
.srch-row{display:flex;gap:8px;margin-bottom:12px}
.srch-in{flex:1;background:var(--sf);border:1px solid var(--bd);color:var(--tx);font-family:var(--mono);font-size:14px;padding:10px 12px;outline:none;transition:border-color .15s}
.srch-in:focus{border-color:var(--gn)}
.srch-in::placeholder{color:var(--mu)}
.btn-p{background:var(--gd);border:1px solid var(--gn);color:var(--gn);font-family:var(--ui);font-weight:700;font-size:13px;letter-spacing:1.5px;text-transform:uppercase;padding:10px 16px;cursor:pointer;white-space:nowrap;transition:background .15s}
.btn-p:hover:not(:disabled){background:#166534}
.btn-p:disabled{opacity:.35;cursor:default}
.res-row{background:var(--sf);border:1px solid var(--bd);padding:11px 13px;margin-bottom:6px;display:flex;gap:10px;align-items:flex-start;cursor:pointer;text-decoration:none;color:inherit;transition:border-color .15s}
.res-row:hover{border-color:var(--gn)}
.res-sc{font-size:13px;color:var(--gn);min-width:38px;text-align:right;font-weight:bold;flex-shrink:0}
.res-art{font-size:13px;color:var(--tx)}
.res-sec{font-size:11px;color:var(--mu);margin-top:2px}

/* Radio */
.freq-disp{background:var(--el);border:1px solid var(--bd);padding:18px 14px;margin-bottom:10px;text-align:center}
.freq-num{font-size:40px;color:var(--am);letter-spacing:3px;line-height:1}
.freq-unit{font-size:12px;color:var(--mu);margin-top:4px;font-family:var(--ui);letter-spacing:3px;text-transform:uppercase}
.freq-mode{font-family:var(--ui);font-size:12px;letter-spacing:2px;color:var(--am);text-transform:uppercase;margin-top:6px;font-weight:700}
.preset-scroll{display:flex;gap:7px;overflow-x:auto;padding-bottom:8px;scrollbar-width:none;margin-bottom:10px}
.preset-scroll::-webkit-scrollbar{display:none}
.chip{background:var(--el);border:1px solid var(--bd);color:var(--tx);font-family:var(--ui);font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:8px 13px;cursor:pointer;white-space:nowrap;flex-shrink:0;transition:all .15s}
.chip:hover{border-color:var(--am);color:var(--am)}
.chip.act{border-color:var(--am);color:var(--am);background:#451a03}
.alert-row{border-left:3px solid var(--am);background:var(--sf);padding:10px 12px;margin-bottom:6px}
.alert-type{font-family:var(--ui);font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--am);margin-bottom:3px}
.alert-text{font-size:13px;color:var(--tx);line-height:1.4}

/* Notes */
.note-ta{width:100%;background:var(--sf);border:1px solid var(--bd);color:var(--tx);font-family:var(--mono);font-size:13px;padding:10px 12px;resize:none;outline:none;height:72px;transition:border-color .15s;line-height:1.5}
.note-ta:focus{border-color:var(--gn)}
.note-ta::placeholder{color:var(--mu)}
.char-ct{font-size:10px;color:var(--mu);text-align:right;margin:4px 0 8px;font-family:var(--ui);letter-spacing:1px}
.char-ct.warn{color:var(--am)}
.note-card{background:var(--sf);border:1px solid var(--bd);padding:11px 13px;margin-bottom:6px}
.note-txt{font-size:13px;color:var(--tx);line-height:1.5;margin-bottom:6px}
.note-meta{font-size:10px;color:var(--mu);font-family:var(--ui);letter-spacing:1px;text-transform:uppercase}

/* Modal */
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.75);display:flex;align-items:flex-end;z-index:100;backdrop-filter:blur(2px)}
.sheet{background:var(--sf);border-top:2px solid var(--gn);width:100%;padding:20px 14px 36px;animation:slideUp .2s ease}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
.modal-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}
.modal-title{font-family:var(--ui);font-size:15px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--gn)}
.fld-lbl{font-family:var(--ui);font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:var(--mu);margin-bottom:5px}
.fld-in{width:100%;background:var(--el);border:1px solid var(--bd);color:var(--tx);font-family:var(--mono);font-size:14px;padding:10px 12px;outline:none;margin-bottom:12px;transition:border-color .15s}
.fld-in:focus{border-color:var(--gn)}
.fld-hint{font-size:11px;color:var(--mu);margin-bottom:16px;line-height:1.5}
.btn-full{background:var(--gd);border:1px solid var(--gn);color:var(--gn);font-family:var(--ui);font-weight:700;font-size:14px;letter-spacing:2px;text-transform:uppercase;padding:12px 20px;cursor:pointer;width:100%;transition:background .15s}
.btn-full:hover{background:#166534}

/* Loading */
.dots{display:inline-flex;gap:4px;align-items:center}
.dots span{width:5px;height:5px;background:var(--gn);border-radius:50%;animation:dot 1.4s ease infinite}
.dots span:nth-child(2){animation-delay:.2s}.dots span:nth-child(3){animation-delay:.4s}
@keyframes dot{0%,80%,100%{opacity:.2;transform:scale(.8)}40%{opacity:1;transform:scale(1)}}

/* Empty state */
.empty{text-align:center;padding:36px 20px;color:var(--mu);font-size:13px;line-height:1.7}
.empty-tag{font-size:10px;font-family:var(--ui);font-weight:700;letter-spacing:2.5px;text-transform:uppercase;margin-bottom:10px}

/* Warn card */
.warn-card{background:#3d1f00;border:1px solid #7c3a00;padding:11px 13px;margin-bottom:10px}
.warn-title{font-family:var(--ui);font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:var(--am);margin-bottom:4px}
.warn-body{font-size:12px;color:#fde68a;line-height:1.5}

/* Peer */
.peer-row{background:var(--sf);border:1px solid var(--bd);padding:11px 13px;margin-bottom:6px;display:flex;align-items:center;gap:10px}
.peer-fp{font-size:13px;color:var(--gn);font-family:var(--mono);flex:1}
.peer-trust{font-size:10px;font-family:var(--ui);font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:2px 7px}
.peer-trust.trusted{background:var(--gd);color:var(--gn)}
.peer-trust.unverified{background:var(--el);color:var(--mu)}
`;

/* ─── LOADING DOTS ───────────────────────────────────────────── */
const Dots = () => <div className="dots"><span/><span/><span/></div>;

/* ─── STATUS SCREEN ──────────────────────────────────────────── */
function StatusScreen({ status }) {
  if (!status) return <div className="scr"><div className="empty"><Dots /><div style={{marginTop:12}}>Polling pod…</div></div></div>;
  const { uptime_seconds, load_avg, storage, voltage, dhcp_clients, time_source, build_version, services } = status;
  const used = storage.kiwix_bytes_total - storage.kiwix_bytes_free;
  const pct = Math.round((used / storage.kiwix_bytes_total) * 100);
  const svcList = [
    { k: "retrieve", n: "Library" }, { k: "assist", n: "Assist" }, { k: "listen", n: "Radio" },
    { k: "notes", n: "Notes" }, { k: "mesh", n: "Mesh" }, { k: "adsb", n: "ADS-B" },
  ];
  return (
    <div className="scr">
      <div className="sh">System</div>
      <div className="sg">
        <div className="st"><div className="sl">Uptime</div><div className="sv">{fmtUptime(uptime_seconds)}</div><div className="ss">time: {time_source}</div></div>
        <div className="st"><div className="sl">Clients</div><div className="sv">{dhcp_clients}</div><div className="ss">DHCP leases</div></div>
        <div className="st"><div className="sl">Load</div><div className="sv" style={{fontSize:18}}>{load_avg[0].toFixed(2)}</div><div className="ss">{load_avg[1].toFixed(2)} · {load_avg[2].toFixed(2)}</div></div>
        <div className="st"><div className="sl">Version</div><div className="sv" style={{fontSize:14,paddingTop:4}}>{build_version}</div><div className="ss" style={{color: voltage.undervoltage ? "var(--rd)" : "var(--mu)"}}>{voltage.undervoltage ? "⚠ undervolt" : "power ok"}</div></div>
      </div>

      <div className="sh">Storage</div>
      <div className="card">
        <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
          <span style={{fontSize:11,color:"var(--mu)",fontFamily:"var(--ui)",fontWeight:700,letterSpacing:1,textTransform:"uppercase"}}>Kiwix Library</span>
          <span style={{fontSize:12,color:"var(--gn)"}}>{fmtBytes(used)} / {fmtBytes(storage.kiwix_bytes_total)}</span>
        </div>
        <div className="pbar"><div className="pbar-fill" style={{width:`${pct}%`,background: pct > 85 ? "var(--am)" : undefined}} /></div>
        <div style={{fontSize:10,color:"var(--mu)",marginTop:5,textAlign:"right",fontFamily:"var(--ui)",letterSpacing:1}}>{pct}% USED</div>
      </div>

      <div className="sh">Services</div>
      <div className="svc-grid">
        {svcList.map(({ k, n }) => {
          const st = services[k] || "unknown";
          const c = svcColor(st);
          return (
            <div className="svc" key={k}>
              <div className="svc-dot" style={{ backgroundColor: c, boxShadow: `0 0 5px ${c}` }} />
              <div className="svc-n" style={{ color: st === "ready" ? "var(--tx)" : "var(--mu)" }}>{n}</div>
              <div className="svc-s">{st === "ready" ? "ready" : st === "not-running" ? "offline" : "unknown"}</div>
            </div>
          );
        })}
      </div>

      {services.mesh === "ready" && services.mesh_fingerprint && (
        <>
          <div className="sh">Mesh Identity</div>
          <div className="card">
            <div style={{fontSize:10,color:"var(--mu)",fontFamily:"var(--ui)",fontWeight:700,letterSpacing:1.5,textTransform:"uppercase",marginBottom:5}}>Fingerprint</div>
            <div style={{fontSize:15,color:"var(--gn)",letterSpacing:3,fontFamily:"var(--mono)"}}>{services.mesh_fingerprint}</div>
          </div>
        </>
      )}

      {services.adsb_aircraft > 0 && (
        <div className="card" style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <span style={{fontSize:11,color:"var(--mu)",fontFamily:"var(--ui)",fontWeight:700,letterSpacing:1.5,textTransform:"uppercase"}}>ADS-B Aircraft</span>
          <span style={{fontSize:18,color:"var(--bl)",fontFamily:"var(--mono)"}}>{services.adsb_aircraft}</span>
        </div>
      )}
    </div>
  );
}

/* ─── ASK SCREEN ─────────────────────────────────────────────── */
function AskScreen({ podUrl, isDemo, assistReady }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const histRef = useRef(null);

  const scrollBottom = () => { if (histRef.current) histRef.current.scrollTop = histRef.current.scrollHeight; };
  useEffect(scrollBottom, [messages, loading]);

  const ask = async () => {
    if (!query.trim() || loading) return;
    const q = query.trim();
    setQuery(""); setLoading(true);
    if (isDemo || !assistReady) {
      await new Promise(r => setTimeout(r, 900 + Math.random() * 600));
      setMessages(m => [...m, { q, r: MOCK.ask }]);
    } else {
      try {
        const res = await fetch(`${podUrl}/api/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ q }), signal: AbortSignal.timeout(30000) });
        const data = await res.json();
        setMessages(m => [...m, { q, r: data }]);
      } catch { setMessages(m => [...m, { q, r: { mode: "error", answer: "No response from pod assistant.", citations: [] } }]); }
    }
    setLoading(false);
  };

  return (
    <div className="ask-wrap">
      <div className="ask-hist" ref={histRef}>
        {!assistReady && !isDemo && <div className="warn-card"><div className="warn-title">Assist not running</div><div className="warn-body">Pi 5 with model weights + index required. Library search still available.</div></div>}
        {messages.length === 0 && !loading && (
          <div className="empty">
            <div className="empty-tag" style={{color:"var(--gn)"}}>Library-Grounded Q&A</div>
            <div>Answers are grounded in the offline Kiwix library. No internet required.</div>
            <div style={{marginTop:14,fontSize:12,color:"var(--mu)"}}>Try: "how to purify water" · "treating burns" · "emergency shelter construction"</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i}>
            <div className="msg-q"><div className="msg-q-text">{m.q}</div></div>
            <div className="msg-a">
              <div className={`mode-badge ${m.r.mode}`}>{m.r.mode === "answer" ? "✓ answer" : m.r.mode === "defer" ? "⚠ defer" : m.r.mode === "error" ? "✗ error" : "— no answer"}</div>
              {m.r.confidence !== undefined && <div className="conf">CONFIDENCE: <span style={{color: m.r.confidence > 0.7 ? "var(--gn)" : "var(--am)"}}>{(m.r.confidence * 100).toFixed(0)}%</span></div>}
              <div className="ans-text">{m.r.answer}</div>
              {m.r.citations?.length > 0 && (
                <div className="cites">
                  <div style={{fontSize:10,color:"var(--mu)",fontFamily:"var(--ui)",fontWeight:700,letterSpacing:1.5,textTransform:"uppercase",marginBottom:3}}>Sources</div>
                  {m.r.citations.map(c => (
                    <div key={c.number} className="cite-row">
                      <span className="cite-n">[{c.number}]</span>
                      <span>{c.article} → {c.section}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <div className="empty"><Dots /><div style={{marginTop:10,fontSize:12}}>Querying library…</div></div>}
      </div>
      <div className="ask-bar">
        <div className="ask-row">
          <textarea className="ask-ta" value={query} onChange={e => setQuery(e.target.value)} placeholder="Ask the library…" rows={1}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); ask(); } }} />
          <button className="btn-send" onClick={ask} disabled={!query.trim() || loading}><Ic name="send" size={17} /></button>
        </div>
      </div>
    </div>
  );
}

/* ─── SEARCH SCREEN ──────────────────────────────────────────── */
function SearchScreen({ podUrl, isDemo }) {
  const [q, setQ] = useState(""); const [loading, setLoading] = useState(false); const [results, setResults] = useState(null);
  const go = async () => {
    if (!q.trim() || loading) return;
    setLoading(true);
    if (isDemo) { await new Promise(r => setTimeout(r, 500)); setResults(MOCK.retrieve); }
    else {
      try {
        const res = await fetch(`${podUrl}/api/retrieve?q=${encodeURIComponent(q)}&k=8`, { signal: AbortSignal.timeout(10000) });
        const data = await res.json();
        setResults(data.results || []);
      } catch { setResults([]); }
    }
    setLoading(false);
  };
  return (
    <div className="scr">
      <div className="srch-row">
        <input className="srch-in" value={q} onChange={e => setQ(e.target.value)} placeholder="Search the library…" onKeyDown={e => e.key === "Enter" && go()} />
        <button className="btn-p" onClick={go} disabled={!q.trim() || loading}>{loading ? <Dots /> : "Go"}</button>
      </div>
      {results === null && <div className="empty"><div className="empty-tag" style={{color:"var(--bl)"}}>Knowledge Library</div><div>Wikipedia · iFixit · Survival guides · WikEM clinical · Regional maps — all offline.</div></div>}
      {results?.length === 0 && <div className="empty">No results for "{q}"</div>}
      {results?.map((r, i) => (
        <a key={i} className="res-row" href={podUrl + r.url} target="_blank" rel="noopener noreferrer">
          <div className="res-sc">{(r.score * 100).toFixed(0)}%</div>
          <div><div className="res-art">{r.article}</div><div className="res-sec">§ {r.section}</div></div>
        </a>
      ))}
    </div>
  );
}

/* ─── RADIO SCREEN ───────────────────────────────────────────── */
function RadioScreen({ podUrl, isDemo, listenReady }) {
  const [presets, setPresets] = useState(MOCK.presets);
  const [alerts, setAlerts] = useState([]);
  const [tuned, setTuned] = useState(null);
  const [state, setState] = useState({ freq_mhz: 162.400, mode: "NFM", status: "idle" });

  useEffect(() => {
    if (isDemo) { setAlerts(MOCK.alerts); return; }
    const poll = async () => {
      try {
        const [sr, ar, pr] = await Promise.all([
          fetch(`${podUrl}/api/listen/state`), fetch(`${podUrl}/api/listen/alerts`), fetch(`${podUrl}/api/listen/presets`)
        ]);
        if (sr.ok) setState(await sr.json());
        if (ar.ok) { const d = await ar.json(); setAlerts(d.alerts || []); }
        if (pr.ok) { const d = await pr.json(); setPresets(d.presets || MOCK.presets); }
      } catch {}
    };
    poll(); const t = setInterval(poll, 5000); return () => clearInterval(t);
  }, [podUrl, isDemo]);

  const tune = async (p) => {
    setTuned(p.label);
    if (isDemo) { setState({ freq_mhz: p.freq_mhz, mode: p.mode, status: "receiving" }); return; }
    try { await fetch(`${podUrl}/api/listen/tune`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ freq_mhz: p.freq_mhz, mode: p.mode }) }); } catch {}
  };

  return (
    <div className="scr">
      {!listenReady && !isDemo && <div className="warn-card"><div className="warn-title">Radio offline</div><div className="warn-body">RTL-SDR dongle (e.g. RTL-SDR Blog v4) not detected. Plug in a compatible USB SDR device and restart.</div></div>}
      <div className="freq-disp">
        <div className="freq-num">{state.freq_mhz?.toFixed?.(3) ?? "162.400"}</div>
        <div className="freq-unit">MHz</div>
        <div className="freq-mode">{state.mode ?? "NFM"} · {state.status ?? "idle"}</div>
      </div>
      <div className="sh">Presets</div>
      <div className="preset-scroll">
        {presets.map(p => <button key={p.label} className={`chip ${tuned === p.label ? "act" : ""}`} onClick={() => tune(p)}>{p.label}</button>)}
      </div>
      <div className="sh">Alerts</div>
      {alerts.length === 0 && <div className="card" style={{textAlign:"center",color:"var(--mu)",fontSize:12}}>No active alerts</div>}
      {alerts.map((a, i) => (
        <div key={i} className="alert-row">
          <div className="alert-type">{a.type} · {fmtAgo(a.ts)}</div>
          <div className="alert-text">{a.event}{a.area ? ` — ${a.area}` : ""}</div>
        </div>
      ))}
    </div>
  );
}

/* ─── BOARD SCREEN ───────────────────────────────────────────── */
function BoardScreen({ podUrl, isDemo }) {
  const [notes, setNotes] = useState([]);
  const [text, setText] = useState(""); const [posting, setPosting] = useState(false); const [err, setErr] = useState(null);
  const MAX = 280;

  const load = useCallback(async () => {
    if (isDemo) { setNotes(MOCK.notes); return; }
    try { const res = await fetch(`${podUrl}/api/notes?limit=100`); const d = await res.json(); setNotes(d.notes || []); } catch {}
  }, [podUrl, isDemo]);

  useEffect(() => { load(); }, [load]);

  const post = async () => {
    if (!text.trim() || posting || text.length > MAX) return;
    setPosting(true); setErr(null);
    if (isDemo) {
      await new Promise(r => setTimeout(r, 400));
      setNotes(n => [{ id: `d${Date.now()}`, text: text.trim(), ts: Date.now() }, ...n]);
      setText(""); setPosting(false); return;
    }
    try {
      const res = await fetch(`${podUrl}/api/notes`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: text.trim() }) });
      if (res.ok) { setText(""); load(); } else setErr("Post rejected by pod.");
    } catch { setErr("Could not reach pod."); }
    setPosting(false);
  };

  return (
    <div className="scr">
      <div className="sh">Post a note</div>
      <textarea className="note-ta" value={text} onChange={e => setText(e.target.value)} placeholder="Community info, resources, safety updates…" maxLength={MAX} />
      <div className={`char-ct ${text.length > MAX - 40 ? "warn" : ""}`}>{text.length} / {MAX}</div>
      {err && <div style={{color:"var(--rd)",fontSize:12,marginBottom:8}}>{err}</div>}
      <button className="btn-p" style={{width:"100%",marginBottom:16}} onClick={post} disabled={!text.trim() || posting || text.length > MAX}>{posting ? "Posting…" : "Post to Board"}</button>
      <div className="sh">Board</div>
      {notes.length === 0 && <div className="empty">No notes yet. Be the first to post.</div>}
      {notes.map(n => (
        <div key={n.id} className="note-card">
          <div className="note-txt">{n.text}</div>
          <div className="note-meta">{fmtAgo(n.ts)}</div>
        </div>
      ))}
    </div>
  );
}

/* ─── SETTINGS MODAL ─────────────────────────────────────────── */
function Settings({ podUrl, onSave, onClose, isDemo }) {
  const [url, setUrl] = useState(podUrl);
  return (
    <div className="overlay" onClick={onClose}>
      <div className="sheet" onClick={e => e.stopPropagation()}>
        <div className="modal-hdr">
          <div className="modal-title">⚙ Pod Settings</div>
          <button className="btn-ic" onClick={onClose}><Ic name="x" size={20} /></button>
        </div>
        <div className="fld-lbl">Pod Address</div>
        <input className="fld-in" value={url} onChange={e => setUrl(e.target.value)} placeholder="http://192.168.4.1" />
        <div className="fld-hint">Join the <strong style={{color:"var(--gn)"}}>RPI-HUB-INFOHUB</strong> Wi-Fi network first. The pod is always at <code style={{color:"var(--gn)"}}>http://192.168.4.1</code> or <code style={{color:"var(--gn)"}}>http://hub.local</code>. No internet required.</div>
        <div className="fld-lbl">Current mode</div>
        <div style={{fontSize:13,color: isDemo ? "var(--am)" : "var(--gn)",fontFamily:"var(--mono)",padding:"8px 0 14px"}}>
          {isDemo ? "◉ DEMO — mock data" : "◉ LIVE — pod reachable"}
        </div>
        <button className="btn-full" onClick={() => onSave(url.replace(/\/+$/, ""))}>Connect</button>
      </div>
    </div>
  );
}

/* ─── APP ROOT ───────────────────────────────────────────────── */
export default function App() {
  const [tab, setTab] = useState("status");
  const [podUrl, setPodUrl] = useState(DEFAULT_POD);
  const [status, setStatus] = useState(null);
  const [conn, setConn] = useState("demo");
  const [showSettings, setShowSettings] = useState(false);
  const [isDemo, setIsDemo] = useState(true);

  // Auto-detect pod
  useEffect(() => {
    const h = typeof window !== "undefined" ? window.location.hostname : "";
    if (h === "192.168.4.1" || h === "hub.local") {
      setIsDemo(false); setPodUrl(""); setConn("online");
    } else {
      setIsDemo(true); setStatus(MOCK.status); setConn("demo");
    }
  }, []);

  // Poll status
  useEffect(() => {
    if (isDemo) { setStatus(MOCK.status); setConn("demo"); return; }
    let alive = true;
    const poll = async () => {
      if (!alive) return;
      try {
        const res = await fetch(`${podUrl}/api/status`, { signal: AbortSignal.timeout(4000) });
        if (res.ok && alive) { setStatus(await res.json()); setConn("online"); }
      } catch { if (alive) { setConn(c => c === "demo" ? "demo" : "offline"); } }
    };
    poll(); const t = setInterval(poll, 6000);
    return () => { alive = false; clearInterval(t); };
  }, [podUrl, isDemo]);

  const svcs = status?.services || {};
  const bars = { online: 4, demo: 2, connecting: 1, offline: 0 }[conn] ?? 0;

  const TABS = [
    { id: "status", label: "Status", icon: "home" },
    { id: "search", label: "Search", icon: "search" },
    { id: "ask", label: "Ask", icon: "chat" },
    { id: "radio", label: "Radio", icon: "antenna" },
    { id: "board", label: "Board", icon: "clipboard" },
  ];

  return (
    <>
      <style>{CSS}</style>
      <div style={{display:"flex",flexDirection:"column",height:"100dvh",background:"var(--bg)"}}>
        {/* Header */}
        <div className="hdr">
          <div>
            <div className="logo">rpi-hub</div>
            <div className="logo-sub">OFFLINE INFOHUB</div>
          </div>
          <div style={{flex:1}} />
          <div style={{display:"flex",alignItems:"center",gap:8}}>
            <div className="sig-bars">{[1,2,3,4].map(i => <div key={i} className={`sig-bar${i<=bars?" on":""}`} />)}</div>
            <div className={`conn-lbl ${conn}`}>{conn}</div>
          </div>
          <button className="btn-ic" onClick={() => setShowSettings(true)}><Ic name="settings" size={18} /></button>
        </div>

        {/* Demo banner */}
        {isDemo && (
          <div className="demo-baner">
            <Ic name="wifi" size={14} color="var(--am)" />
            DEMO — join RPI-HUB-INFOHUB Wi-Fi · tap ⚙ to connect
          </div>
        )}

        {/* Content */}
        {tab === "ask" ? (
          <div style={{flex:1,overflow:"hidden",display:"flex",flexDirection:"column"}}>
            <AskScreen podUrl={podUrl} isDemo={isDemo} assistReady={svcs.assist === "ready"} />
          </div>
        ) : (
          <div className="main">
            {tab === "status" && <StatusScreen status={status} />}
            {tab === "search" && <SearchScreen podUrl={podUrl} isDemo={isDemo} />}
            {tab === "radio" && <RadioScreen podUrl={podUrl} isDemo={isDemo} listenReady={svcs.listen === "ready"} />}
            {tab === "board" && <BoardScreen podUrl={podUrl} isDemo={isDemo} />}
          </div>
        )}

        {/* Bottom nav */}
        <div className="bnav">
          {TABS.map(t => (
            <button key={t.id} className={`nb${tab===t.id?" act":""}`} onClick={() => setTab(t.id)}>
              <Ic name={t.icon} size={21} color={tab===t.id?"#4ade80":"#5a7a5a"} />
              {t.label}
            </button>
          ))}
        </div>

        {/* Settings modal */}
        {showSettings && (
          <Settings
            podUrl={podUrl}
            isDemo={isDemo}
            onSave={(url) => { setPodUrl(url); setIsDemo(false); setConn("connecting"); setShowSettings(false); }}
            onClose={() => setShowSettings(false)}
          />
        )}
      </div>
    </>
  );
}
