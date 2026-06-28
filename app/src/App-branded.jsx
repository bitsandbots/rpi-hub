import { useState, useEffect, useCallback, useRef } from "react";

/* ═══════════════════════════════════════════════════════════════
   rpi-hub Mobile App Interface — CoreConduit Silver v2.1
   Deploy to: www/portal/app/ (Vite-built SPA)
   When served from 192.168.4.1 / hub.local, app auto-connects.
   Otherwise defaults to demo mode with mock data.
════════════════════════════════════════════════════════════════ */

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
const svcColor = (s) => ({ ready: "#1a9a4a", "not-running": "#636a76", unknown: "#c08a15" }[s] || "#c08a15");

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
@import url('https://fonts.googleapis.com/css2?family=Exo+2:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root{
  --cc-silver-950:#2a2f38;
  --cc-silver-900:#3a404a;
  --cc-silver-800:#4d545f;
  --cc-silver-700:#636a76;
  --cc-silver-600:#7d8491;
  --cc-silver-500:#969daa;
  --cc-silver-400:#a8aeb9;
  --cc-silver-300:#bfc4cc;
  --cc-silver-200:#d2d6dc;
  --cc-silver-150:#dfe2e7;
  --cc-silver-100:#eaecf0;
  --cc-silver-50:#f2f3f6;

  --cc-bg-base:#c5c9d0;
  --cc-bg-panel:#cdd1d8;
  --cc-bg-card:#d8dbe1;
  --cc-bg-elevated:#e2e5ea;
  --cc-bg-input:#bcc0c8;
  --cc-bg-hover:#b5b9c2;

  --cc-border-subtle:#b8bcc4;
  --cc-border:#a8adb6;
  --cc-border-strong:#969ba5;

  --cc-text-primary:#1e232b;
  --cc-text-secondary:#3a404a;
  --cc-text-muted:#636a76;
  --cc-text-faint:#7d8491;
  --cc-text-on-dark:#eaecf0;
  --cc-text-on-accent:#ffffff;

  --cc-blue-600:#1b6ad4;
  --cc-blue-500:#2b7de9;
  --cc-blue-400:#4a9eff;
  --cc-blue-300:#6bb3ff;
  --cc-blue-200:#a3d1ff;
  --cc-blue-glow:rgba(43,125,233,0.12);
  --cc-blue-glow-strong:rgba(43,125,233,0.22);

  --cc-orange-600:#c55d0a;
  --cc-orange-500:#e07018;
  --cc-orange-400:#f08030;
  --cc-orange-300:#ffa05c;
  --cc-orange-200:#ffc49e;
  --cc-orange-glow:rgba(224,112,24,0.12);

  --cc-navy-900:#0b1220;
  --cc-navy-800:#0f1a2e;
  --cc-navy-700:#152240;
  --cc-navy-600:#1c2d52;

  --cc-success:#1a9a4a;
  --cc-success-bg:rgba(26,154,74,0.1);
  --cc-warning:#c08a15;
  --cc-warning-bg:rgba(192,138,21,0.1);
  --cc-error:#d43030;
  --cc-error-bg:rgba(212,48,48,0.1);

  --cc-font-display:'Exo 2',sans-serif;
  --cc-font-body:'Plus Jakarta Sans',sans-serif;
  --cc-font-mono:'IBM Plex Mono',monospace;

  --cc-radius-sm:6px;
  --cc-radius-md:10px;
  --cc-radius-lg:14px;

  --cc-shadow-sm:0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
  --cc-shadow-card:0 2px 8px rgba(0,0,0,0.1), 0 1px 3px rgba(0,0,0,0.06);
  --cc-shadow-elevated:0 8px 24px rgba(0,0,0,0.12), 0 2px 6px rgba(0,0,0,0.08);
  --cc-shadow-blue:0 2px 12px rgba(43,125,233,0.2);
  --cc-shadow-orange:0 2px 12px rgba(224,112,24,0.2);
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

body{background:var(--cc-bg-base);color:var(--cc-text-primary);font-family:var(--cc-font-body);overflow:hidden;-webkit-font-smoothing:antialiased}
#root{display:flex;flex-direction:column;height:100dvh;max-width:480px;margin:0 auto}

/* Header — dark navy CoreConduit topbar */
.hdr{background:var(--cc-navy-800);border-bottom:1px solid var(--cc-navy-700);padding:10px 14px;display:flex;align-items:center;gap:10px;flex-shrink:0}
.hdr::after{content:'';position:absolute;bottom:-1px;left:0;right:0;height:1px;background:linear-gradient(90deg,var(--cc-blue-500),var(--cc-orange-500));opacity:.6}
.logo-mini{width:28px;height:28px;border-radius:6px;background:linear-gradient(135deg,var(--cc-blue-500),var(--cc-orange-500));display:flex;align-items:center;justify-content:center;font-family:var(--cc-font-display);font-size:10px;font-weight:800;color:white;flex-shrink:0}
.logo{font-family:var(--cc-font-display);font-weight:700;font-size:1rem;color:var(--cc-text-on-dark);letter-spacing:0.02em;line-height:1}
.logo .accent{color:var(--cc-orange-400)}
.logo-sub{font-size:9px;color:var(--cc-silver-500);font-weight:500;letter-spacing:0.08em;font-family:var(--cc-font-mono);text-transform:uppercase;margin-top:1px}
.sig-bars{display:flex;align-items:flex-end;gap:2.5px;height:16px}
.sig-bar{width:3px;background:var(--cc-navy-600);border-radius:1px;transition:background .3s}
.sig-bar.on{background:var(--cc-blue-400);box-shadow:0 0 4px var(--cc-blue-400)}
.sig-bar:nth-child(1){height:4px}.sig-bar:nth-child(2){height:7px}.sig-bar:nth-child(3){height:10px}.sig-bar:nth-child(4){height:14px}
.conn-lbl{font-size:9px;letter-spacing:0.08em;text-transform:uppercase;font-family:var(--cc-font-mono);font-weight:600}
.conn-lbl.demo{color:var(--cc-warning)}.conn-lbl.online{color:var(--cc-success)}.conn-lbl.offline{color:var(--cc-error)}.conn-lbl.connecting{color:var(--cc-blue-400)}
.btn-ic{background:none;border:none;color:var(--cc-silver-400);cursor:pointer;padding:5px;border-radius:var(--cc-radius-sm);display:flex;align-items:center;justify-content:center;transition:color .15s}
.btn-ic:hover{color:var(--cc-text-on-dark)}

/* Demo banner */
.demo-baner{background:var(--cc-orange-glow);border-bottom:1px solid var(--cc-orange-500);border-left:3px solid var(--cc-orange-500);color:var(--cc-orange-600);font-size:10px;font-family:var(--cc-font-body);font-weight:600;letter-spacing:0.02em;text-align:center;padding:6px 14px;display:flex;align-items:center;justify-content:center;gap:7px;flex-shrink:0}

/* Main scroll */
.main{flex:1;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.main::-webkit-scrollbar{display:none}

/* Bottom nav — dark navy CoreConduit style */
.bnav{background:var(--cc-navy-800);border-top:1px solid var(--cc-navy-700);display:flex;flex-shrink:0;padding-bottom:env(safe-area-inset-bottom,0px)}
.nb{flex:1;background:none;border:none;cursor:pointer;padding:8px 0 6px;display:flex;flex-direction:column;align-items:center;gap:3px;font-family:var(--cc-font-body);font-size:9px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;color:var(--cc-silver-400);transition:color .15s}
.nb.act{color:var(--cc-blue-400)}.nb:hover:not(.act){color:var(--cc-text-on-dark)}

/* Screen */
.scr{padding:14px 14px;animation:fadeIn .12s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:translateY(0)}}

/* Sec header */
.sh{font-family:var(--cc-font-mono);font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--cc-text-muted);margin-bottom:8px;display:flex;align-items:center;gap:8px}
.sh::after{content:'';flex:1;height:1px;background:var(--cc-border)}

/* Stat grid */
.sg{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:10px}
.st{background:var(--cc-bg-card);border:1px solid var(--cc-border-subtle);padding:12px;box-shadow:var(--cc-shadow-sm);border-radius:var(--cc-radius-sm)}
.sl{font-size:9px;color:var(--cc-text-muted);letter-spacing:0.08em;text-transform:uppercase;font-family:var(--cc-font-mono);font-weight:500;margin-bottom:3px}
.sv{font-size:1.4rem;font-family:var(--cc-font-display);font-weight:800;line-height:1;color:var(--cc-blue-500)}
.ss{font-size:9px;color:var(--cc-text-faint);margin-top:3px;font-family:var(--cc-font-mono)}

/* Services */
.svc-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:10px}
.svc{background:var(--cc-bg-card);border:1px solid var(--cc-border-subtle);border-radius:var(--cc-radius-md);padding:10px 6px;display:flex;flex-direction:column;align-items:center;gap:4px;position:relative;box-shadow:var(--cc-shadow-sm)}
.svc-dot{width:6px;height:6px;border-radius:50%;position:absolute;top:5px;right:5px}
.svc-n{font-family:var(--cc-font-display);font-size:11px;font-weight:700;letter-spacing:0.02em;text-transform:uppercase;text-align:center}
.svc-s{font-size:8px;color:var(--cc-text-faint);text-transform:uppercase;font-family:var(--cc-font-mono);letter-spacing:0.04em}

/* Card */
.card{background:var(--cc-bg-card);border:1px solid var(--cc-border-subtle);border-radius:var(--cc-radius-md);padding:12px 14px;margin-bottom:8px;box-shadow:var(--cc-shadow-sm);position:relative;overflow:hidden}
.card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--cc-blue-500),var(--cc-orange-500))}

/* Progress */
.pbar{height:4px;background:var(--cc-bg-input);margin-top:6px;border-radius:2px}
.pbar-fill{height:100%;background:linear-gradient(90deg,var(--cc-blue-500),var(--cc-blue-400));transition:width .4s;border-radius:2px}

/* Ask */
.ask-wrap{display:flex;flex-direction:column;height:100%}
.ask-hist{flex:1;overflow-y:auto;padding:14px;scrollbar-width:none}
.ask-hist::-webkit-scrollbar{display:none}
.ask-bar{border-top:1px solid var(--cc-border);padding:10px 14px;background:var(--cc-bg-base);flex-shrink:0}
.ask-row{display:flex;gap:8px}
.ask-ta{flex:1;background:var(--cc-bg-input);border:1px solid var(--cc-border);color:var(--cc-text-primary);font-family:var(--cc-font-body);font-size:13px;padding:10px 12px;resize:none;outline:none;min-height:44px;max-height:100px;line-height:1.4;transition:border-color .15s;border-radius:var(--cc-radius-sm)}
.ask-ta:focus{border-color:var(--cc-blue-500);box-shadow:var(--cc-shadow-blue)}
.ask-ta::placeholder{color:var(--cc-text-faint)}
.btn-send{background:var(--cc-blue-600);border:none;color:white;cursor:pointer;width:44px;height:44px;display:flex;align-items:center;justify-content:center;transition:all .15s;flex-shrink:0;border-radius:var(--cc-radius-sm);box-shadow:var(--cc-shadow-blue)}
.btn-send:hover:not(:disabled){background:var(--cc-blue-500);box-shadow:0 4px 16px rgba(43,125,233,0.3);transform:translateY(-1px)}
.btn-send:disabled{opacity:.35;cursor:default;box-shadow:none}

/* Msg bubbles */
.msg-q{text-align:right;margin-bottom:12px}
.msg-q-text{display:inline-block;background:var(--cc-bg-elevated);border:1px solid var(--cc-border-subtle);padding:8px 12px;font-size:13px;max-width:80%;text-align:left;color:var(--cc-text-primary);border-radius:var(--cc-radius-sm);font-family:var(--cc-font-body)}
.msg-a{margin-bottom:14px}
.mode-badge{display:inline-flex;align-items:center;gap:4px;font-family:var(--cc-font-mono);font-size:9px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;padding:2px 8px;margin-bottom:8px;border-radius:4px}
.mode-badge.answer{background:var(--cc-success-bg);color:var(--cc-success)}
.mode-badge.defer{background:var(--cc-orange-glow);color:var(--cc-orange-600)}
.mode-badge.noanswer,.mode-badge.error{background:var(--cc-bg-card);color:var(--cc-text-faint)}
.conf{font-size:9px;color:var(--cc-text-faint);margin-bottom:6px;font-family:var(--cc-font-mono);letter-spacing:0.04em}
.ans-text{font-size:13px;line-height:1.65;color:var(--cc-text-secondary)}
.cites{margin-top:8px;border-top:1px solid var(--cc-border-subtle);padding-top:8px;display:flex;flex-direction:column;gap:3px}
.cite-row{font-size:11px;color:var(--cc-blue-600);display:flex;gap:6px;font-family:var(--cc-font-body)}
.cite-n{color:var(--cc-text-faint);font-family:var(--cc-font-mono)}

/* Search */
.srch-row{display:flex;gap:8px;margin-bottom:12px}
.srch-in{flex:1;background:var(--cc-bg-input);border:1px solid var(--cc-border);color:var(--cc-text-primary);font-family:var(--cc-font-body);font-size:13px;padding:10px 12px;outline:none;border-radius:var(--cc-radius-sm);transition:border-color .15s}
.srch-in:focus{border-color:var(--cc-blue-500);box-shadow:var(--cc-shadow-blue)}
.srch-in::placeholder{color:var(--cc-text-faint)}
.btn-p{background:var(--cc-blue-600);border:none;color:white;font-family:var(--cc-font-display);font-weight:700;font-size:12px;letter-spacing:0.05em;text-transform:uppercase;padding:10px 16px;cursor:pointer;white-space:nowrap;border-radius:var(--cc-radius-sm);box-shadow:var(--cc-shadow-blue);transition:all .15s}
.btn-p:hover:not(:disabled){background:var(--cc-blue-500);box-shadow:0 4px 16px rgba(43,125,233,0.3);transform:translateY(-1px)}
.btn-p:disabled{opacity:.35;cursor:default;box-shadow:none}
.res-row{background:var(--cc-bg-card);border:1px solid var(--cc-border-subtle);border-radius:var(--cc-radius-sm);padding:11px 13px;margin-bottom:6px;display:flex;gap:10px;align-items:flex-start;cursor:pointer;text-decoration:none;color:inherit;transition:all .15s;box-shadow:var(--cc-shadow-sm)}
.res-row:hover{border-color:var(--cc-blue-500);box-shadow:var(--cc-shadow-blue);transform:translateY(-1px)}
.res-sc{font-size:13px;color:var(--cc-blue-600);min-width:38px;text-align:right;font-weight:700;font-family:var(--cc-font-display);flex-shrink:0}
.res-art{font-size:13px;color:var(--cc-text-primary);font-family:var(--cc-font-display);font-weight:600}
.res-sec{font-size:11px;color:var(--cc-text-muted);margin-top:2px;font-family:var(--cc-font-body)}

/* Radio */
.freq-disp{background:var(--cc-bg-card);border:1px solid var(--cc-border-subtle);border-radius:var(--cc-radius-md);padding:18px 14px;margin-bottom:10px;text-align:center;box-shadow:var(--cc-shadow-sm)}
.freq-disp::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--cc-blue-500),var(--cc-orange-500))}
.freq-num{font-size:2.4rem;color:var(--cc-orange-500);letter-spacing:0.02em;line-height:1;font-family:var(--cc-font-display);font-weight:800}
.freq-unit{font-size:11px;color:var(--cc-text-faint);margin-top:4px;font-family:var(--cc-font-mono);letter-spacing:0.1em;text-transform:uppercase}
.freq-mode{font-family:var(--cc-font-mono);font-size:11px;letter-spacing:0.08em;color:var(--cc-orange-600);text-transform:uppercase;margin-top:6px;font-weight:600}
.preset-scroll{display:flex;gap:7px;overflow-x:auto;padding-bottom:8px;scrollbar-width:none;margin-bottom:10px}
.preset-scroll::-webkit-scrollbar{display:none}
.chip{background:var(--cc-bg-card);border:1px solid var(--cc-border-subtle);color:var(--cc-text-secondary);font-family:var(--cc-font-body);font-size:11px;font-weight:600;letter-spacing:0.03em;text-transform:uppercase;padding:8px 13px;cursor:pointer;white-space:nowrap;flex-shrink:0;transition:all .15s;border-radius:var(--cc-radius-sm)}
.chip:hover{border-color:var(--cc-orange-500);color:var(--cc-orange-600);box-shadow:var(--cc-shadow-orange)}
.chip.act{border-color:var(--cc-orange-500);color:var(--cc-orange-500);background:var(--cc-orange-glow)}
.alert-row{background:var(--cc-bg-card);border-left:3px solid var(--cc-orange-500);padding:10px 12px;margin-bottom:6px;border-radius:0 var(--cc-radius-sm) var(--cc-radius-sm) 0;box-shadow:var(--cc-shadow-sm)}
.alert-type{font-family:var(--cc-font-mono);font-size:9px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:var(--cc-orange-600);margin-bottom:3px}
.alert-text{font-size:12px;color:var(--cc-text-secondary);line-height:1.4;font-family:var(--cc-font-body)}

/* Notes */
.note-ta{width:100%;background:var(--cc-bg-input);border:1px solid var(--cc-border);color:var(--cc-text-primary);font-family:var(--cc-font-body);font-size:13px;padding:10px 12px;resize:none;outline:none;height:72px;border-radius:var(--cc-radius-sm);transition:border-color .15s;line-height:1.5}
.note-ta:focus{border-color:var(--cc-blue-500);box-shadow:var(--cc-shadow-blue)}
.note-ta::placeholder{color:var(--cc-text-faint)}
.char-ct{font-size:9px;color:var(--cc-text-faint);text-align:right;margin:4px 0 8px;font-family:var(--cc-font-mono);letter-spacing:0.04em}
.char-ct.warn{color:var(--cc-orange-600)}
.note-card{background:var(--cc-bg-card);border:1px solid var(--cc-border-subtle);border-radius:var(--cc-radius-sm);padding:11px 13px;margin-bottom:6px;box-shadow:var(--cc-shadow-sm)}
.note-txt{font-size:13px;color:var(--cc-text-secondary);line-height:1.5;margin-bottom:6px;font-family:var(--cc-font-body)}
.note-meta{font-size:9px;color:var(--cc-text-faint);font-family:var(--cc-font-mono);letter-spacing:0.04em;text-transform:uppercase}

/* Modal */
.overlay{position:fixed;inset:0;background:rgba(30,35,43,0.75);display:flex;align-items:flex-end;z-index:100;backdrop-filter:blur(2px)}
.sheet{background:var(--cc-bg-panel);border-top:2px solid var(--cc-blue-500);width:100%;padding:20px 14px 36px;animation:slideUp .2s ease;border-radius:var(--cc-radius-lg) var(--cc-radius-lg) 0 0}
@keyframes slideUp{from{transform:translateY(100%)}to{transform:translateY(0)}}
.modal-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}
.modal-title{font-family:var(--cc-font-display);font-size:15px;font-weight:700;letter-spacing:0.03em;text-transform:uppercase;color:var(--cc-text-primary)}
.fld-lbl{font-family:var(--cc-font-mono);font-size:9px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--cc-text-muted);margin-bottom:5px}
.fld-in{width:100%;background:var(--cc-bg-input);border:1px solid var(--cc-border);color:var(--cc-text-primary);font-family:var(--cc-font-mono);font-size:13px;padding:10px 12px;outline:none;margin-bottom:12px;border-radius:var(--cc-radius-sm);transition:border-color .15s}
.fld-in:focus{border-color:var(--cc-blue-500);box-shadow:var(--cc-shadow-blue)}
.fld-hint{font-size:11px;color:var(--cc-text-muted);margin-bottom:16px;line-height:1.5;font-family:var(--cc-font-body)}
.fld-hint strong{color:var(--cc-blue-600)}
.fld-hint code{font-family:var(--cc-font-mono);font-size:11px;background:var(--cc-bg-hover);padding:1px 5px;border-radius:3px;color:var(--cc-blue-600)}
.btn-full{background:linear-gradient(135deg,var(--cc-blue-600),var(--cc-blue-500));border:none;color:white;font-family:var(--cc-font-display);font-weight:700;font-size:13px;letter-spacing:0.05em;text-transform:uppercase;padding:12px 20px;cursor:pointer;width:100%;border-radius:var(--cc-radius-sm);box-shadow:var(--cc-shadow-blue);transition:all .15s}
.btn-full:hover{background:linear-gradient(135deg,var(--cc-blue-500),var(--cc-blue-400));box-shadow:0 4px 16px rgba(43,125,233,0.3);transform:translateY(-1px)}

/* Loading */
.dots{display:inline-flex;gap:4px;align-items:center}
.dots span{width:5px;height:5px;background:var(--cc-blue-500);border-radius:50%;animation:dot 1.4s ease infinite}
.dots span:nth-child(2){animation-delay:.2s}.dots span:nth-child(3){animation-delay:.4s}
@keyframes dot{0%,80%,100%{opacity:.2;transform:scale(.8)}40%{opacity:1;transform:scale(1)}}

/* Empty state */
.empty{text-align:center;padding:36px 20px;color:var(--cc-text-muted);font-size:13px;line-height:1.7;font-family:var(--cc-font-body)}
.empty-tag{font-size:10px;font-family:var(--cc-font-mono);font-weight:600;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:10px}

/* Warn card */
.warn-card{background:var(--cc-orange-glow);border:1px solid var(--cc-orange-500);border-left:3px solid var(--cc-orange-500);padding:11px 13px;margin-bottom:10px;border-radius:0 var(--cc-radius-sm) var(--cc-radius-sm) 0}
.warn-title{font-family:var(--cc-font-display);font-size:10px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;color:var(--cc-orange-600);margin-bottom:4px}
.warn-body{font-size:12px;color:var(--cc-orange-600);line-height:1.5;font-family:var(--cc-font-body)}

/* Peer */
.peer-row{background:var(--cc-bg-card);border:1px solid var(--cc-border-subtle);border-radius:var(--cc-radius-sm);padding:11px 13px;margin-bottom:6px;display:flex;align-items:center;gap:10px;box-shadow:var(--cc-shadow-sm)}
.peer-fp{font-size:12px;color:var(--cc-blue-600);font-family:var(--cc-font-mono);font-weight:500;flex:1}
.peer-trust{font-size:9px;font-family:var(--cc-font-mono);font-weight:600;letter-spacing:0.04em;text-transform:uppercase;padding:2px 7px;border-radius:4px}
.peer-trust.trusted{background:var(--cc-success-bg);color:var(--cc-success)}
.peer-trust.unverified{background:var(--cc-bg-elevated);color:var(--cc-text-faint)}
`;

/* ─── LOADING DOTS ───────────────────────────────────────────── */
const Dots = () => <div className="dots"><span/><span/><span/></div>;

/* ═══════════════════════════════════════════════════════════════
   SCREENS — Same logic as original, new CSS tokens
════════════════════════════════════════════════════════════════ */

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
        <div className="st"><div className="sl">Load</div><div className="sv" style={{fontSize:"1.1rem",paddingTop:4}}>{load_avg[0].toFixed(2)}</div><div className="ss">{load_avg[1].toFixed(2)} · {load_avg[2].toFixed(2)}</div></div>
        <div className="st"><div className="sl">Version</div><div className="sv" style={{fontSize:"1rem",paddingTop:4,color:"var(--cc-text-primary)"}}>{build_version}</div><div className="ss" style={{color: voltage.undervoltage ? "var(--cc-error)" : "var(--cc-text-faint)"}}>{voltage.undervoltage ? "⚠ undervolt" : "power ok"}</div></div>
      </div>

      <div className="sh">Storage</div>
      <div className="card" style={{paddingTop:15}}>
        <div style={{display:"flex",justifyContent:"space-between",marginBottom:6}}>
          <span style={{fontSize:10,color:"var(--cc-text-muted)",fontFamily:"var(--cc-font-mono)",fontWeight:600,letterSpacing:"0.04em",textTransform:"uppercase"}}>Kiwix Library</span>
          <span style={{fontSize:12,color:"var(--cc-blue-600)",fontFamily:"var(--cc-font-display)",fontWeight:700}}>{fmtBytes(used)} / {fmtBytes(storage.kiwix_bytes_total)}</span>
        </div>
        <div className="pbar"><div className="pbar-fill" style={{width:`${pct}%`,background: pct>85 ? `linear-gradient(90deg,var(--cc-orange-500),var(--cc-orange-400))` : undefined}} /></div>
        <div style={{fontSize:9,color:"var(--cc-text-faint)",marginTop:5,textAlign:"right",fontFamily:"var(--cc-font-mono)",letterSpacing:"0.04em"}}>{pct}% USED</div>
      </div>

      <div className="sh">Services</div>
      <div className="svc-grid">
        {svcList.map(({ k, n }) => {
          const st = services[k] || "unknown";
          const c = svcColor(st);
          return (
            <div className="svc" key={k}>
              <div className="svc-dot" style={{ backgroundColor: c, boxShadow: `0 0 5px ${c}` }} />
              <div className="svc-n" style={{ color: st === "ready" ? "var(--cc-text-primary)" : "var(--cc-text-muted)" }}>{n}</div>
              <div className="svc-s">{st === "ready" ? "ready" : st === "not-running" ? "offline" : "unknown"}</div>
            </div>
          );
        })}
      </div>

      {services.mesh === "ready" && services.mesh_fingerprint && (
        <>
          <div className="sh">Mesh Identity</div>
          <div className="card" style={{paddingTop:15}}>
            <div style={{fontSize:9,color:"var(--cc-text-muted)",fontFamily:"var(--cc-font-mono)",fontWeight:600,letterSpacing:"0.06em",textTransform:"uppercase",marginBottom:5}}>Fingerprint</div>
            <div style={{fontSize:14,color:"var(--cc-blue-600)",letterSpacing:"0.04em",fontFamily:"var(--cc-font-mono)",fontWeight:500}}>{services.mesh_fingerprint}</div>
          </div>
        </>
      )}

      {services.adsb_aircraft > 0 && (
        <div className="card" style={{paddingTop:15,display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <span style={{fontSize:10,color:"var(--cc-text-muted)",fontFamily:"var(--cc-font-mono)",fontWeight:600,letterSpacing:"0.06em",textTransform:"uppercase"}}>ADS-B Aircraft</span>
          <span style={{fontSize:1.1+"rem",color:"var(--cc-blue-500)",fontFamily:"var(--cc-font-display)",fontWeight:800}}>{services.adsb_aircraft}</span>
        </div>
      )}
    </div>
  );
}

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
            <div className="empty-tag" style={{color:"var(--cc-blue-500)"}}>Library-Grounded Q&A</div>
            <div>Answers are grounded in the offline Kiwix library. No internet required.</div>
            <div style={{marginTop:14,fontSize:12,color:"var(--cc-text-muted)"}}>Try: "how to purify water" · "treating burns" · "emergency shelter construction"</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i}>
            <div className="msg-q"><div className="msg-q-text">{m.q}</div></div>
            <div className="msg-a">
              <div className={`mode-badge ${m.r.mode}`}>{m.r.mode === "answer" ? "✓ answer" : m.r.mode === "defer" ? "⚠ defer" : m.r.mode === "error" ? "✗ error" : "— no answer"}</div>
              {m.r.confidence !== undefined && <div className="conf">CONFIDENCE: <span style={{color: m.r.confidence > 0.7 ? "var(--cc-success)" : "var(--cc-warning)"}}>{(m.r.confidence * 100).toFixed(0)}%</span></div>}
              <div className="ans-text">{m.r.answer}</div>
              {m.r.citations?.length > 0 && (
                <div className="cites">
                  <div style={{fontSize:9,color:"var(--cc-text-faint)",fontFamily:"var(--cc-font-mono)",fontWeight:600,letterSpacing:"0.04em",textTransform:"uppercase",marginBottom:3}}>Sources</div>
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
      {results === null && <div className="empty"><div className="empty-tag" style={{color:"var(--cc-blue-500)"}}>Knowledge Library</div><div>Wikipedia · iFixit · Survival guides · WikEM clinical · Regional maps — all offline.</div></div>}
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
      <div className="sh">Current</div>
      <div className="card" style={{padding:"18px 14px",textAlign:"center",marginBottom:10}}>
        <div style={{fontSize:"2.4rem",color:"var(--cc-orange-500)",fontFamily:"var(--cc-font-display)",fontWeight:800,letterSpacing:"0.02em",lineHeight:1}}>{state.freq_mhz?.toFixed?.(3) ?? "162.400"}</div>
        <div style={{fontSize:11,color:"var(--cc-text-faint)",fontFamily:"var(--cc-font-mono)",letterSpacing:"0.1em",textTransform:"uppercase",marginTop:4}}>MHz</div>
        <div style={{fontSize:11,fontFamily:"var(--cc-font-mono)",letterSpacing:"0.08em",color:"var(--cc-orange-600)",textTransform:"uppercase",marginTop:6,fontWeight:600}}>{state.mode ?? "NFM"} · {state.status ?? "idle"}</div>
      </div>
      <div className="sh">Presets</div>
      <div className="preset-scroll">
        {presets.map(p => <button key={p.label} className={`chip ${tuned === p.label ? "act" : ""}`} onClick={() => tune(p)}>{p.label}</button>)}
      </div>
      <div className="sh">Alerts</div>
      {alerts.length === 0 && <div className="card" style={{paddingTop:15,textAlign:"center",color:"var(--cc-text-muted)",fontSize:12}}>No active alerts</div>}
      {alerts.map((a, i) => (
        <div key={i} className="alert-row">
          <div className="alert-type">{a.type} · {fmtAgo(a.ts)}</div>
          <div className="alert-text">{a.event}{a.area ? ` — ${a.area}` : ""}</div>
        </div>
      ))}
    </div>
  );
}

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
      {err && <div style={{color:"var(--cc-error)",fontSize:12,marginBottom:8}}>{err}</div>}
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

function Settings({ podUrl, onSave, onClose, isDemo }) {
  const [url, setUrl] = useState(podUrl);
  return (
    <div className="overlay" onClick={onClose}>
      <div className="sheet" onClick={e => e.stopPropagation()}>
        <div className="modal-hdr">
          <div className="modal-title">Pod Settings</div>
          <button className="btn-ic" onClick={onClose}><Ic name="x" size={20} /></button>
        </div>
        <div className="fld-lbl">Pod Address</div>
        <input className="fld-in" value={url} onChange={e => setUrl(e.target.value)} placeholder="http://192.168.4.1" />
        <div className="fld-hint">Join the <strong>RPI-HUB-INFOHUB</strong> Wi-Fi network first. The pod is always at <code>http://192.168.4.1</code> or <code>http://hub.local</code>. No internet required.</div>
        <div className="fld-lbl">Current mode</div>
        <div style={{fontSize:13,color:isDemo?"var(--cc-orange-600)":"var(--cc-success)",fontFamily:"var(--cc-font-mono)",padding:"8px 0 14px",fontWeight:500}}>
          {isDemo ? "◉ DEMO — mock data" : "◉ LIVE — pod reachable"}
        </div>
        <button className="btn-full" onClick={() => onSave(url.replace(/\/+$/, ""))}>Connect</button>
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("status");
  const [podUrl, setPodUrl] = useState(DEFAULT_POD);
  const [status, setStatus] = useState(null);
  const [conn, setConn] = useState("demo");
  const [showSettings, setShowSettings] = useState(false);
  const [isDemo, setIsDemo] = useState(true);

  useEffect(() => {
    const h = typeof window !== "undefined" ? window.location.hostname : "";
    if (h === "192.168.4.1" || h === "hub.local") {
      setIsDemo(false); setPodUrl(""); setConn("online");
    } else {
      setIsDemo(true); setStatus(MOCK.status); setConn("demo");
    }
  }, []);

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
      <div style={{display:"flex",flexDirection:"column",height:"100dvh",background:"var(--cc-bg-base)"}}>
        {/* Header — CoreConduit dark navy topbar */}
        <div className="hdr">
          <div className="logo-mini">rP</div>
          <div>
            <div className="logo">rpi<span className="accent">-POD</span></div>
            <div className="logo-sub">Offline InfoHub</div>
          </div>
          <div style={{flex:1}} />
          <div style={{display:"flex",alignItems:"center",gap:10}}>
            <div className="sig-bars">{[1,2,3,4].map(i => <div key={i} className={`sig-bar${i<=bars?" on":""}`} />)}</div>
            <div className={`conn-lbl ${conn}`}>{conn}</div>
          </div>
          <button className="btn-ic" onClick={() => setShowSettings(true)}><Ic name="settings" size={18} /></button>
        </div>

        {/* Demo banner */}
        {isDemo && (
          <div className="demo-baner">
            <Ic name="wifi" size={14} color="var(--cc-orange-500)" />
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

        {/* Bottom nav — CoreConduit dark navy */}
        <div className="bnav">
          {TABS.map(t => (
            <button key={t.id} className={`nb${tab===t.id?" act":""}`} onClick={() => setTab(t.id)}>
              <Ic name={t.icon} size={21} color={tab===t.id?"#4a9eff":"#636a76"} />
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
