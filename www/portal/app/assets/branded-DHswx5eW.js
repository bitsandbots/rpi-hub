import{r as n,j as e,c as z}from"./client-D_4IY7PA.js";const M="http://192.168.4.1",b={status:{uptime_seconds:86741,load_avg:[.18,.12,.09],storage:{kiwix_bytes_free:186e8,kiwix_bytes_total:64e9},voltage:{throttled:"0x0",undervoltage:!1},dhcp_clients:4,time_source:"rtc",build_version:"v1.2.1",services:{retrieve:"ready",assist:"not-running",listen:"ready",notes:"ready",mesh:"ready",adsb:"not-running",adsb_aircraft:0,mesh_fingerprint:"A3F7-92BC-E15D-40F8"}},notes:[{id:"n1",text:"Water distribution at the community center — open until 6 PM.",ts:Date.now()-32e5},{id:"n2",text:"Oak Ave bridge is passable. No flooding reported.",ts:Date.now()-71e5},{id:"n3",text:"Mobile charging station active at Fire Station 12 on Main St.",ts:Date.now()-108e5},{id:"n4",text:"Medical volunteers at Eastside Church. Open to all.",ts:Date.now()-18e6}],retrieve:[{article:"Water purification",section:"Boiling methods",score:.94,url:"/library/A/Water_purification"},{article:"Water purification",section:"Chemical treatment",score:.87,url:"/library/A/Water_purification"},{article:"Emergency management",section:"Water supply",score:.73,url:"/library/A/Emergency_management"},{article:"Wilderness survival",section:"Finding water",score:.68,url:"/library/A/Wilderness_survival"}],ask:{mode:"answer",answer:`To purify water in an emergency:
1. Boil vigorously for 1 minute (3 min above 6,500 ft elevation).
2. If boiling is not possible, use 2 drops of unscented bleach (6%) per liter and wait 30 min.
3. Iodine or chlorine tablets work at standard dosage; follow package directions.
4. Always filter visibly cloudy water through cloth before any treatment.`,citations:[{number:1,article:"Water purification",section:"Boiling",url:"/library/A/Water_purification"},{number:2,article:"Water purification",section:"Chemical treatment",url:"/library/A/Water_purification"}],confidence:.91},presets:[{label:"NOAA WX1",freq_mhz:162.4,mode:"NFM"},{label:"NOAA WX2",freq_mhz:162.425,mode:"NFM"},{label:"NOAA WX3",freq_mhz:162.45,mode:"NFM"},{label:"NOAA WX4",freq_mhz:162.475,mode:"NFM"},{label:"FM 91.5",freq_mhz:91.5,mode:"WFM"},{label:"AM 1620",freq_mhz:1.62,mode:"AM"}],alerts:[{type:"NOAA SAME",event:"Winter Storm Watch",area:"Inland Empire / San Bernardino Mtns",ts:Date.now()-24e5}],peers:[{id:"p1",fingerprint:"B2E8-71AC-D34F-89F1",trust:"TRUSTED",last_seen:Date.now()-118e3},{id:"p2",fingerprint:"C9F1-83BD-E56G-90H2",trust:"UNVERIFIED",last_seen:Date.now()-84e4}]},A=r=>{const o=Math.floor(r/86400),t=Math.floor(r%86400/3600),i=Math.floor(r%3600/60);return o>0?`${o}d ${t}h`:t>0?`${t}h ${i}m`:`${i}m ${Math.floor(r%60)}s`},N=r=>r>1e9?`${(r/1e9).toFixed(1)} GB`:r>1e6?`${(r/1e6).toFixed(0)} MB`:`${Math.round(r/1e3)} KB`,S=r=>{const o=Date.now()-r;return o<6e4?"just now":o<36e5?`${Math.floor(o/6e4)}m ago`:o<864e5?`${Math.floor(o/36e5)}h ago`:`${Math.floor(o/864e5)}d ago`},_=r=>({ready:"#1a9a4a","not-running":"#636a76",unknown:"#c08a15"})[r]||"#c08a15",C={home:"M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10",search:"M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z",chat:"M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z",radio:"M2.5 19h19M9 8a3 3 0 016 0v7H9V8zM12 3v1",clipboard:"M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",settings:"M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06-.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z",x:"M18 6L6 18M6 6l12 12",send:"M22 2L11 13M22 2L15 22l-4-9-9-4z",alert:"M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01",wifi:"M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01",antenna:"M2 12a10 10 0 0020 0M5 12a7 7 0 0014 0M8 12a4 4 0 018 0M12 12v8M12 4v2"},w=({name:r,size:o=20,color:t="currentColor"})=>e.jsx("svg",{width:o,height:o,viewBox:"0 0 24 24",fill:"none",stroke:t,strokeWidth:"1.8",strokeLinecap:"round",strokeLinejoin:"round",children:(C[r]||"").split("M").filter(Boolean).map((i,c)=>e.jsx("path",{d:"M"+i},c))}),F=`
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
`,k=()=>e.jsxs("div",{className:"dots",children:[e.jsx("span",{}),e.jsx("span",{}),e.jsx("span",{})]});function T({status:r}){if(!r)return e.jsx("div",{className:"scr",children:e.jsxs("div",{className:"empty",children:[e.jsx(k,{}),e.jsx("div",{style:{marginTop:12},children:"Polling pod…"})]})});const{uptime_seconds:o,load_avg:t,storage:i,voltage:c,dhcp_clients:f,time_source:x,build_version:m,services:g}=r,s=i.kiwix_bytes_total-i.kiwix_bytes_free,d=Math.round(s/i.kiwix_bytes_total*100),v=[{k:"retrieve",n:"Library"},{k:"assist",n:"Assist"},{k:"listen",n:"Radio"},{k:"notes",n:"Notes"},{k:"mesh",n:"Mesh"},{k:"adsb",n:"ADS-B"}];return e.jsxs("div",{className:"scr",children:[e.jsx("div",{className:"sh",children:"System"}),e.jsxs("div",{className:"sg",children:[e.jsxs("div",{className:"st",children:[e.jsx("div",{className:"sl",children:"Uptime"}),e.jsx("div",{className:"sv",children:A(o)}),e.jsxs("div",{className:"ss",children:["time: ",x]})]}),e.jsxs("div",{className:"st",children:[e.jsx("div",{className:"sl",children:"Clients"}),e.jsx("div",{className:"sv",children:f}),e.jsx("div",{className:"ss",children:"DHCP leases"})]}),e.jsxs("div",{className:"st",children:[e.jsx("div",{className:"sl",children:"Load"}),e.jsx("div",{className:"sv",style:{fontSize:"1.1rem",paddingTop:4},children:t[0].toFixed(2)}),e.jsxs("div",{className:"ss",children:[t[1].toFixed(2)," · ",t[2].toFixed(2)]})]}),e.jsxs("div",{className:"st",children:[e.jsx("div",{className:"sl",children:"Version"}),e.jsx("div",{className:"sv",style:{fontSize:"1rem",paddingTop:4,color:"var(--cc-text-primary)"},children:m}),e.jsx("div",{className:"ss",style:{color:c.undervoltage?"var(--cc-error)":"var(--cc-text-faint)"},children:c.undervoltage?"⚠ undervolt":"power ok"})]})]}),e.jsx("div",{className:"sh",children:"Storage"}),e.jsxs("div",{className:"card",style:{paddingTop:15},children:[e.jsxs("div",{style:{display:"flex",justifyContent:"space-between",marginBottom:6},children:[e.jsx("span",{style:{fontSize:10,color:"var(--cc-text-muted)",fontFamily:"var(--cc-font-mono)",fontWeight:600,letterSpacing:"0.04em",textTransform:"uppercase"},children:"Kiwix Library"}),e.jsxs("span",{style:{fontSize:12,color:"var(--cc-blue-600)",fontFamily:"var(--cc-font-display)",fontWeight:700},children:[N(s)," / ",N(i.kiwix_bytes_total)]})]}),e.jsx("div",{className:"pbar",children:e.jsx("div",{className:"pbar-fill",style:{width:`${d}%`,background:d>85?"linear-gradient(90deg,var(--cc-orange-500),var(--cc-orange-400))":void 0}})}),e.jsxs("div",{style:{fontSize:9,color:"var(--cc-text-faint)",marginTop:5,textAlign:"right",fontFamily:"var(--cc-font-mono)",letterSpacing:"0.04em"},children:[d,"% USED"]})]}),e.jsx("div",{className:"sh",children:"Services"}),e.jsx("div",{className:"svc-grid",children:v.map(({k:a,n:l})=>{const h=g[a]||"unknown",p=_(h);return e.jsxs("div",{className:"svc",children:[e.jsx("div",{className:"svc-dot",style:{backgroundColor:p,boxShadow:`0 0 5px ${p}`}}),e.jsx("div",{className:"svc-n",style:{color:h==="ready"?"var(--cc-text-primary)":"var(--cc-text-muted)"},children:l}),e.jsx("div",{className:"svc-s",children:h==="ready"?"ready":h==="not-running"?"offline":"unknown"})]},a)})}),g.mesh==="ready"&&g.mesh_fingerprint&&e.jsxs(e.Fragment,{children:[e.jsx("div",{className:"sh",children:"Mesh Identity"}),e.jsxs("div",{className:"card",style:{paddingTop:15},children:[e.jsx("div",{style:{fontSize:9,color:"var(--cc-text-muted)",fontFamily:"var(--cc-font-mono)",fontWeight:600,letterSpacing:"0.06em",textTransform:"uppercase",marginBottom:5},children:"Fingerprint"}),e.jsx("div",{style:{fontSize:14,color:"var(--cc-blue-600)",letterSpacing:"0.04em",fontFamily:"var(--cc-font-mono)",fontWeight:500},children:g.mesh_fingerprint})]})]}),g.adsb_aircraft>0&&e.jsxs("div",{className:"card",style:{paddingTop:15,display:"flex",justifyContent:"space-between",alignItems:"center"},children:[e.jsx("span",{style:{fontSize:10,color:"var(--cc-text-muted)",fontFamily:"var(--cc-font-mono)",fontWeight:600,letterSpacing:"0.06em",textTransform:"uppercase"},children:"ADS-B Aircraft"}),e.jsx("span",{style:{fontSize:1.1+"rem",color:"var(--cc-blue-500)",fontFamily:"var(--cc-font-display)",fontWeight:800},children:g.adsb_aircraft})]})]})}function B({podUrl:r,isDemo:o,assistReady:t}){const[i,c]=n.useState(""),[f,x]=n.useState(!1),[m,g]=n.useState([]),s=n.useRef(null),d=()=>{s.current&&(s.current.scrollTop=s.current.scrollHeight)};n.useEffect(d,[m,f]);const v=async()=>{if(!i.trim()||f)return;const a=i.trim();if(c(""),x(!0),o||!t)await new Promise(l=>setTimeout(l,900+Math.random()*600)),g(l=>[...l,{q:a,r:b.ask}]);else try{const h=await(await fetch(`${r}/api/ask`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({q:a}),signal:AbortSignal.timeout(3e4)})).json();g(p=>[...p,{q:a,r:h}])}catch{g(l=>[...l,{q:a,r:{mode:"error",answer:"No response from pod assistant.",citations:[]}}])}x(!1)};return e.jsxs("div",{className:"ask-wrap",children:[e.jsxs("div",{className:"ask-hist",ref:s,children:[!t&&!o&&e.jsxs("div",{className:"warn-card",children:[e.jsx("div",{className:"warn-title",children:"Assist not running"}),e.jsx("div",{className:"warn-body",children:"Pi 5 with model weights + index required. Library search still available."})]}),m.length===0&&!f&&e.jsxs("div",{className:"empty",children:[e.jsx("div",{className:"empty-tag",style:{color:"var(--cc-blue-500)"},children:"Library-Grounded Q&A"}),e.jsx("div",{children:"Answers are grounded in the offline Kiwix library. No internet required."}),e.jsx("div",{style:{marginTop:14,fontSize:12,color:"var(--cc-text-muted)"},children:'Try: "how to purify water" · "treating burns" · "emergency shelter construction"'})]}),m.map((a,l)=>e.jsxs("div",{children:[e.jsx("div",{className:"msg-q",children:e.jsx("div",{className:"msg-q-text",children:a.q})}),e.jsxs("div",{className:"msg-a",children:[e.jsx("div",{className:`mode-badge ${a.r.mode}`,children:a.r.mode==="answer"?"✓ answer":a.r.mode==="defer"?"⚠ defer":a.r.mode==="error"?"✗ error":"— no answer"}),a.r.confidence!==void 0&&e.jsxs("div",{className:"conf",children:["CONFIDENCE: ",e.jsxs("span",{style:{color:a.r.confidence>.7?"var(--cc-success)":"var(--cc-warning)"},children:[(a.r.confidence*100).toFixed(0),"%"]})]}),e.jsx("div",{className:"ans-text",children:a.r.answer}),a.r.citations?.length>0&&e.jsxs("div",{className:"cites",children:[e.jsx("div",{style:{fontSize:9,color:"var(--cc-text-faint)",fontFamily:"var(--cc-font-mono)",fontWeight:600,letterSpacing:"0.04em",textTransform:"uppercase",marginBottom:3},children:"Sources"}),a.r.citations.map(h=>e.jsxs("div",{className:"cite-row",children:[e.jsxs("span",{className:"cite-n",children:["[",h.number,"]"]}),e.jsxs("span",{children:[h.article," → ",h.section]})]},h.number))]})]})]},l)),f&&e.jsxs("div",{className:"empty",children:[e.jsx(k,{}),e.jsx("div",{style:{marginTop:10,fontSize:12},children:"Querying library…"})]})]}),e.jsx("div",{className:"ask-bar",children:e.jsxs("div",{className:"ask-row",children:[e.jsx("textarea",{className:"ask-ta",value:i,onChange:a=>c(a.target.value),placeholder:"Ask the library…",rows:1,onKeyDown:a=>{a.key==="Enter"&&!a.shiftKey&&(a.preventDefault(),v())}}),e.jsx("button",{className:"btn-send",onClick:v,disabled:!i.trim()||f,children:e.jsx(w,{name:"send",size:17})})]})})]})}function P({podUrl:r,isDemo:o}){const[t,i]=n.useState(""),[c,f]=n.useState(!1),[x,m]=n.useState(null),g=async()=>{if(!(!t.trim()||c)){if(f(!0),o)await new Promise(s=>setTimeout(s,500)),m(b.retrieve);else try{const d=await(await fetch(`${r}/api/retrieve?q=${encodeURIComponent(t)}&k=8`,{signal:AbortSignal.timeout(1e4)})).json();m(d.results||[])}catch{m([])}f(!1)}};return e.jsxs("div",{className:"scr",children:[e.jsxs("div",{className:"srch-row",children:[e.jsx("input",{className:"srch-in",value:t,onChange:s=>i(s.target.value),placeholder:"Search the library…",onKeyDown:s=>s.key==="Enter"&&g()}),e.jsx("button",{className:"btn-p",onClick:g,disabled:!t.trim()||c,children:c?e.jsx(k,{}):"Go"})]}),x===null&&e.jsxs("div",{className:"empty",children:[e.jsx("div",{className:"empty-tag",style:{color:"var(--cc-blue-500)"},children:"Knowledge Library"}),e.jsx("div",{children:"Wikipedia · iFixit · Survival guides · WikEM clinical · Regional maps — all offline."})]}),x?.length===0&&e.jsxs("div",{className:"empty",children:['No results for "',t,'"']}),x?.map((s,d)=>e.jsxs("a",{className:"res-row",href:r+s.url,target:"_blank",rel:"noopener noreferrer",children:[e.jsxs("div",{className:"res-sc",children:[(s.score*100).toFixed(0),"%"]}),e.jsxs("div",{children:[e.jsx("div",{className:"res-art",children:s.article}),e.jsxs("div",{className:"res-sec",children:["§ ",s.section]})]})]},d))]})}function W({podUrl:r,isDemo:o,listenReady:t}){const[i,c]=n.useState(b.presets),[f,x]=n.useState([]),[m,g]=n.useState(null),[s,d]=n.useState({freq_mhz:162.4,mode:"NFM",status:"idle"});n.useEffect(()=>{if(o){x(b.alerts);return}const a=async()=>{try{const[h,p,u]=await Promise.all([fetch(`${r}/api/listen/state`),fetch(`${r}/api/listen/alerts`),fetch(`${r}/api/listen/presets`)]);if(h.ok&&d(await h.json()),p.ok){const y=await p.json();x(y.alerts||[])}if(u.ok){const y=await u.json();c(y.presets||b.presets)}}catch{}};a();const l=setInterval(a,5e3);return()=>clearInterval(l)},[r,o]);const v=async a=>{if(g(a.label),o){d({freq_mhz:a.freq_mhz,mode:a.mode,status:"receiving"});return}try{await fetch(`${r}/api/listen/tune`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({freq_mhz:a.freq_mhz,mode:a.mode})})}catch{}};return e.jsxs("div",{className:"scr",children:[!t&&!o&&e.jsxs("div",{className:"warn-card",children:[e.jsx("div",{className:"warn-title",children:"Radio offline"}),e.jsx("div",{className:"warn-body",children:"RTL-SDR dongle (e.g. RTL-SDR Blog v4) not detected. Plug in a compatible USB SDR device and restart."})]}),e.jsx("div",{className:"sh",children:"Current"}),e.jsxs("div",{className:"card",style:{padding:"18px 14px",textAlign:"center",marginBottom:10},children:[e.jsx("div",{style:{fontSize:"2.4rem",color:"var(--cc-orange-500)",fontFamily:"var(--cc-font-display)",fontWeight:800,letterSpacing:"0.02em",lineHeight:1},children:s.freq_mhz?.toFixed?.(3)??"162.400"}),e.jsx("div",{style:{fontSize:11,color:"var(--cc-text-faint)",fontFamily:"var(--cc-font-mono)",letterSpacing:"0.1em",textTransform:"uppercase",marginTop:4},children:"MHz"}),e.jsxs("div",{style:{fontSize:11,fontFamily:"var(--cc-font-mono)",letterSpacing:"0.08em",color:"var(--cc-orange-600)",textTransform:"uppercase",marginTop:6,fontWeight:600},children:[s.mode??"NFM"," · ",s.status??"idle"]})]}),e.jsx("div",{className:"sh",children:"Presets"}),e.jsx("div",{className:"preset-scroll",children:i.map(a=>e.jsx("button",{className:`chip ${m===a.label?"act":""}`,onClick:()=>v(a),children:a.label},a.label))}),e.jsx("div",{className:"sh",children:"Alerts"}),f.length===0&&e.jsx("div",{className:"card",style:{paddingTop:15,textAlign:"center",color:"var(--cc-text-muted)",fontSize:12},children:"No active alerts"}),f.map((a,l)=>e.jsxs("div",{className:"alert-row",children:[e.jsxs("div",{className:"alert-type",children:[a.type," · ",S(a.ts)]}),e.jsxs("div",{className:"alert-text",children:[a.event,a.area?` — ${a.area}`:""]})]},l))]})}function E({podUrl:r,isDemo:o}){const[t,i]=n.useState([]),[c,f]=n.useState(""),[x,m]=n.useState(!1),[g,s]=n.useState(null),d=280,v=n.useCallback(async()=>{if(o){i(b.notes);return}try{const h=await(await fetch(`${r}/api/notes?limit=100`)).json();i(h.notes||[])}catch{}},[r,o]);n.useEffect(()=>{v()},[v]);const a=async()=>{if(!(!c.trim()||x||c.length>d)){if(m(!0),s(null),o){await new Promise(l=>setTimeout(l,400)),i(l=>[{id:`d${Date.now()}`,text:c.trim(),ts:Date.now()},...l]),f(""),m(!1);return}try{(await fetch(`${r}/api/notes`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:c.trim()})})).ok?(f(""),v()):s("Post rejected by pod.")}catch{s("Could not reach pod.")}m(!1)}};return e.jsxs("div",{className:"scr",children:[e.jsx("div",{className:"sh",children:"Post a note"}),e.jsx("textarea",{className:"note-ta",value:c,onChange:l=>f(l.target.value),placeholder:"Community info, resources, safety updates…",maxLength:d}),e.jsxs("div",{className:`char-ct ${c.length>d-40?"warn":""}`,children:[c.length," / ",d]}),g&&e.jsx("div",{style:{color:"var(--cc-error)",fontSize:12,marginBottom:8},children:g}),e.jsx("button",{className:"btn-p",style:{width:"100%",marginBottom:16},onClick:a,disabled:!c.trim()||x||c.length>d,children:x?"Posting…":"Post to Board"}),e.jsx("div",{className:"sh",children:"Board"}),t.length===0&&e.jsx("div",{className:"empty",children:"No notes yet. Be the first to post."}),t.map(l=>e.jsxs("div",{className:"note-card",children:[e.jsx("div",{className:"note-txt",children:l.text}),e.jsx("div",{className:"note-meta",children:S(l.ts)})]},l.id))]})}function $({podUrl:r,onSave:o,onClose:t,isDemo:i}){const[c,f]=n.useState(r);return e.jsx("div",{className:"overlay",onClick:t,children:e.jsxs("div",{className:"sheet",onClick:x=>x.stopPropagation(),children:[e.jsxs("div",{className:"modal-hdr",children:[e.jsx("div",{className:"modal-title",children:"Pod Settings"}),e.jsx("button",{className:"btn-ic",onClick:t,children:e.jsx(w,{name:"x",size:20})})]}),e.jsx("div",{className:"fld-lbl",children:"Pod Address"}),e.jsx("input",{className:"fld-in",value:c,onChange:x=>f(x.target.value),placeholder:"http://192.168.4.1"}),e.jsxs("div",{className:"fld-hint",children:["Join the ",e.jsx("strong",{children:"RPI-HUB-INFOHUB"})," Wi-Fi network first. The pod is always at ",e.jsx("code",{children:"http://192.168.4.1"})," or ",e.jsx("code",{children:"http://hub.local"}),". No internet required."]}),e.jsx("div",{className:"fld-lbl",children:"Current mode"}),e.jsx("div",{style:{fontSize:13,color:i?"var(--cc-orange-600)":"var(--cc-success)",fontFamily:"var(--cc-font-mono)",padding:"8px 0 14px",fontWeight:500},children:i?"◉ DEMO — mock data":"◉ LIVE — pod reachable"}),e.jsx("button",{className:"btn-full",onClick:()=>o(c.replace(/\/+$/,"")),children:"Connect"})]})})}function D(){const[r,o]=n.useState("status"),[t,i]=n.useState(M),[c,f]=n.useState(null),[x,m]=n.useState("demo"),[g,s]=n.useState(!1),[d,v]=n.useState(!0);n.useEffect(()=>{const p=typeof window<"u"?window.location.hostname:"";p==="192.168.4.1"||p==="hub.local"?(v(!1),i(""),m("online")):(v(!0),f(b.status),m("demo"))},[]),n.useEffect(()=>{if(d){f(b.status),m("demo");return}let p=!0;const u=async()=>{if(p)try{const j=await fetch(`${t}/api/status`,{signal:AbortSignal.timeout(4e3)});j.ok&&p&&(f(await j.json()),m("online"))}catch{p&&m(j=>j==="demo"?"demo":"offline")}};u();const y=setInterval(u,6e3);return()=>{p=!1,clearInterval(y)}},[t,d]);const a=c?.services||{},l={online:4,demo:2,connecting:1,offline:0}[x]??0,h=[{id:"status",label:"Status",icon:"home"},{id:"search",label:"Search",icon:"search"},{id:"ask",label:"Ask",icon:"chat"},{id:"radio",label:"Radio",icon:"antenna"},{id:"board",label:"Board",icon:"clipboard"}];return e.jsxs(e.Fragment,{children:[e.jsx("style",{children:F}),e.jsxs("div",{style:{display:"flex",flexDirection:"column",height:"100dvh",background:"var(--cc-bg-base)"},children:[e.jsxs("div",{className:"hdr",children:[e.jsx("div",{className:"logo-mini",children:"rP"}),e.jsxs("div",{children:[e.jsxs("div",{className:"logo",children:["rpi",e.jsx("span",{className:"accent",children:"-POD"})]}),e.jsx("div",{className:"logo-sub",children:"Offline InfoHub"})]}),e.jsx("div",{style:{flex:1}}),e.jsxs("div",{style:{display:"flex",alignItems:"center",gap:10},children:[e.jsx("div",{className:"sig-bars",children:[1,2,3,4].map(p=>e.jsx("div",{className:`sig-bar${p<=l?" on":""}`},p))}),e.jsx("div",{className:`conn-lbl ${x}`,children:x})]}),e.jsx("button",{className:"btn-ic",onClick:()=>s(!0),children:e.jsx(w,{name:"settings",size:18})})]}),d&&e.jsxs("div",{className:"demo-baner",children:[e.jsx(w,{name:"wifi",size:14,color:"var(--cc-orange-500)"}),"DEMO — join RPI-HUB-INFOHUB Wi-Fi · tap ⚙ to connect"]}),r==="ask"?e.jsx("div",{style:{flex:1,overflow:"hidden",display:"flex",flexDirection:"column"},children:e.jsx(B,{podUrl:t,isDemo:d,assistReady:a.assist==="ready"})}):e.jsxs("div",{className:"main",children:[r==="status"&&e.jsx(T,{status:c}),r==="search"&&e.jsx(P,{podUrl:t,isDemo:d}),r==="radio"&&e.jsx(W,{podUrl:t,isDemo:d,listenReady:a.listen==="ready"}),r==="board"&&e.jsx(E,{podUrl:t,isDemo:d})]}),e.jsx("div",{className:"bnav",children:h.map(p=>e.jsxs("button",{className:`nb${r===p.id?" act":""}`,onClick:()=>o(p.id),children:[e.jsx(w,{name:p.icon,size:21,color:r===p.id?"#4a9eff":"#636a76"}),p.label]},p.id))}),g&&e.jsx($,{podUrl:t,isDemo:d,onSave:p=>{i(p),v(!1),m("connecting"),s(!1)},onClose:()=>s(!1)})]})]})}z.createRoot(document.getElementById("root")).render(e.jsx(n.StrictMode,{children:e.jsx(D,{})}));
