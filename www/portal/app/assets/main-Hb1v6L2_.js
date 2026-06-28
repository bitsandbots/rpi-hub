import{r as o,j as e,c as z}from"./client-D_4IY7PA.js";const M="http://192.168.4.1",u={status:{uptime_seconds:86741,load_avg:[.18,.12,.09],storage:{kiwix_bytes_free:186e8,kiwix_bytes_total:64e9},voltage:{throttled:"0x0",undervoltage:!1},dhcp_clients:4,time_source:"rtc",build_version:"v1.2.1",services:{retrieve:"ready",assist:"not-running",listen:"ready",notes:"ready",mesh:"ready",adsb:"not-running",adsb_aircraft:0,mesh_fingerprint:"A3F7-92BC-E15D-40F8"}},notes:[{id:"n1",text:"Water distribution at the community center — open until 6 PM.",ts:Date.now()-32e5},{id:"n2",text:"Oak Ave bridge is passable. No flooding reported.",ts:Date.now()-71e5},{id:"n3",text:"Mobile charging station active at Fire Station 12 on Main St.",ts:Date.now()-108e5},{id:"n4",text:"Medical volunteers at Eastside Church. Open to all.",ts:Date.now()-18e6}],retrieve:[{article:"Water purification",section:"Boiling methods",score:.94,url:"/library/A/Water_purification"},{article:"Water purification",section:"Chemical treatment",score:.87,url:"/library/A/Water_purification"},{article:"Emergency management",section:"Water supply",score:.73,url:"/library/A/Emergency_management"},{article:"Wilderness survival",section:"Finding water",score:.68,url:"/library/A/Wilderness_survival"}],ask:{mode:"answer",answer:`To purify water in an emergency:
1. Boil vigorously for 1 minute (3 min above 6,500 ft elevation).
2. If boiling is not possible, use 2 drops of unscented bleach (6%) per liter and wait 30 min.
3. Iodine or chlorine tablets work at standard dosage; follow package directions.
4. Always filter visibly cloudy water through cloth before any treatment.`,citations:[{number:1,article:"Water purification",section:"Boiling",url:"/library/A/Water_purification"},{number:2,article:"Water purification",section:"Chemical treatment",url:"/library/A/Water_purification"}],confidence:.91},presets:[{label:"NOAA WX1",freq_mhz:162.4,mode:"NFM"},{label:"NOAA WX2",freq_mhz:162.425,mode:"NFM"},{label:"NOAA WX3",freq_mhz:162.45,mode:"NFM"},{label:"NOAA WX4",freq_mhz:162.475,mode:"NFM"},{label:"FM 91.5",freq_mhz:91.5,mode:"WFM"},{label:"AM 1620",freq_mhz:1.62,mode:"AM"}],alerts:[{type:"NOAA SAME",event:"Winter Storm Watch",area:"Inland Empire / San Bernardino Mtns",ts:Date.now()-24e5}],peers:[{id:"p1",fingerprint:"B2E8-71AC-D34F-89F1",trust:"TRUSTED",last_seen:Date.now()-118e3},{id:"p2",fingerprint:"C9F1-83BD-E56G-90H2",trust:"UNVERIFIED",last_seen:Date.now()-84e4}]},A=a=>{const s=Math.floor(a/86400),r=Math.floor(a%86400/3600),l=Math.floor(a%3600/60);return s>0?`${s}d ${r}h`:r>0?`${r}h ${l}m`:`${l}m ${Math.floor(a%60)}s`},k=a=>a>1e9?`${(a/1e9).toFixed(1)} GB`:a>1e6?`${(a/1e6).toFixed(0)} MB`:`${Math.round(a/1e3)} KB`,S=a=>{const s=Date.now()-a;return s<6e4?"just now":s<36e5?`${Math.floor(s/6e4)}m ago`:s<864e5?`${Math.floor(s/36e5)}h ago`:`${Math.floor(s/864e5)}d ago`},_=a=>({ready:"#4ade80","not-running":"#2d3f2d",unknown:"#fbbf24"})[a]||"#fbbf24",C={home:"M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10",search:"M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z",chat:"M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z",radio:"M2.5 19h19M9 8a3 3 0 016 0v7H9V8zM12 3v1",clipboard:"M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",settings:"M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06-.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z",x:"M18 6L6 18M6 6l12 12",send:"M22 2L11 13M22 2L15 22l-4-9-9-4z",alert:"M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01",wifi:"M5 12.55a11 11 0 0114.08 0M1.42 9a16 16 0 0121.16 0M8.53 16.11a6 6 0 016.95 0M12 20h.01",antenna:"M2 12a10 10 0 0020 0M5 12a7 7 0 0014 0M8 12a4 4 0 018 0M12 12v8M12 4v2"},j=({name:a,size:s=20,color:r="currentColor"})=>e.jsx("svg",{width:s,height:s,viewBox:"0 0 24 24",fill:"none",stroke:r,strokeWidth:"1.8",strokeLinecap:"round",strokeLinejoin:"round",children:(C[a]||"").split("M").filter(Boolean).map((l,i)=>e.jsx("path",{d:"M"+l},i))}),F=`
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
`,N=()=>e.jsxs("div",{className:"dots",children:[e.jsx("span",{}),e.jsx("span",{}),e.jsx("span",{})]});function B({status:a}){if(!a)return e.jsx("div",{className:"scr",children:e.jsxs("div",{className:"empty",children:[e.jsx(N,{}),e.jsx("div",{style:{marginTop:12},children:"Polling pod…"})]})});const{uptime_seconds:s,load_avg:r,storage:l,voltage:i,dhcp_clients:x,time_source:m,build_version:f,services:h}=a,n=l.kiwix_bytes_total-l.kiwix_bytes_free,d=Math.round(n/l.kiwix_bytes_total*100),v=[{k:"retrieve",n:"Library"},{k:"assist",n:"Assist"},{k:"listen",n:"Radio"},{k:"notes",n:"Notes"},{k:"mesh",n:"Mesh"},{k:"adsb",n:"ADS-B"}];return e.jsxs("div",{className:"scr",children:[e.jsx("div",{className:"sh",children:"System"}),e.jsxs("div",{className:"sg",children:[e.jsxs("div",{className:"st",children:[e.jsx("div",{className:"sl",children:"Uptime"}),e.jsx("div",{className:"sv",children:A(s)}),e.jsxs("div",{className:"ss",children:["time: ",m]})]}),e.jsxs("div",{className:"st",children:[e.jsx("div",{className:"sl",children:"Clients"}),e.jsx("div",{className:"sv",children:x}),e.jsx("div",{className:"ss",children:"DHCP leases"})]}),e.jsxs("div",{className:"st",children:[e.jsx("div",{className:"sl",children:"Load"}),e.jsx("div",{className:"sv",style:{fontSize:18},children:r[0].toFixed(2)}),e.jsxs("div",{className:"ss",children:[r[1].toFixed(2)," · ",r[2].toFixed(2)]})]}),e.jsxs("div",{className:"st",children:[e.jsx("div",{className:"sl",children:"Version"}),e.jsx("div",{className:"sv",style:{fontSize:14,paddingTop:4},children:f}),e.jsx("div",{className:"ss",style:{color:i.undervoltage?"var(--rd)":"var(--mu)"},children:i.undervoltage?"⚠ undervolt":"power ok"})]})]}),e.jsx("div",{className:"sh",children:"Storage"}),e.jsxs("div",{className:"card",children:[e.jsxs("div",{style:{display:"flex",justifyContent:"space-between",marginBottom:6},children:[e.jsx("span",{style:{fontSize:11,color:"var(--mu)",fontFamily:"var(--ui)",fontWeight:700,letterSpacing:1,textTransform:"uppercase"},children:"Kiwix Library"}),e.jsxs("span",{style:{fontSize:12,color:"var(--gn)"},children:[k(n)," / ",k(l.kiwix_bytes_total)]})]}),e.jsx("div",{className:"pbar",children:e.jsx("div",{className:"pbar-fill",style:{width:`${d}%`,background:d>85?"var(--am)":void 0}})}),e.jsxs("div",{style:{fontSize:10,color:"var(--mu)",marginTop:5,textAlign:"right",fontFamily:"var(--ui)",letterSpacing:1},children:[d,"% USED"]})]}),e.jsx("div",{className:"sh",children:"Services"}),e.jsx("div",{className:"svc-grid",children:v.map(({k:t,n:c})=>{const g=h[t]||"unknown",p=_(g);return e.jsxs("div",{className:"svc",children:[e.jsx("div",{className:"svc-dot",style:{backgroundColor:p,boxShadow:`0 0 5px ${p}`}}),e.jsx("div",{className:"svc-n",style:{color:g==="ready"?"var(--tx)":"var(--mu)"},children:c}),e.jsx("div",{className:"svc-s",children:g==="ready"?"ready":g==="not-running"?"offline":"unknown"})]},t)})}),h.mesh==="ready"&&h.mesh_fingerprint&&e.jsxs(e.Fragment,{children:[e.jsx("div",{className:"sh",children:"Mesh Identity"}),e.jsxs("div",{className:"card",children:[e.jsx("div",{style:{fontSize:10,color:"var(--mu)",fontFamily:"var(--ui)",fontWeight:700,letterSpacing:1.5,textTransform:"uppercase",marginBottom:5},children:"Fingerprint"}),e.jsx("div",{style:{fontSize:15,color:"var(--gn)",letterSpacing:3,fontFamily:"var(--mono)"},children:h.mesh_fingerprint})]})]}),h.adsb_aircraft>0&&e.jsxs("div",{className:"card",style:{display:"flex",justifyContent:"space-between",alignItems:"center"},children:[e.jsx("span",{style:{fontSize:11,color:"var(--mu)",fontFamily:"var(--ui)",fontWeight:700,letterSpacing:1.5,textTransform:"uppercase"},children:"ADS-B Aircraft"}),e.jsx("span",{style:{fontSize:18,color:"var(--bl)",fontFamily:"var(--mono)"},children:h.adsb_aircraft})]})]})}function T({podUrl:a,isDemo:s,assistReady:r}){const[l,i]=o.useState(""),[x,m]=o.useState(!1),[f,h]=o.useState([]),n=o.useRef(null),d=()=>{n.current&&(n.current.scrollTop=n.current.scrollHeight)};o.useEffect(d,[f,x]);const v=async()=>{if(!l.trim()||x)return;const t=l.trim();if(i(""),m(!0),s||!r)await new Promise(c=>setTimeout(c,900+Math.random()*600)),h(c=>[...c,{q:t,r:u.ask}]);else try{const g=await(await fetch(`${a}/api/ask`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({q:t}),signal:AbortSignal.timeout(3e4)})).json();h(p=>[...p,{q:t,r:g}])}catch{h(c=>[...c,{q:t,r:{mode:"error",answer:"No response from pod assistant.",citations:[]}}])}m(!1)};return e.jsxs("div",{className:"ask-wrap",children:[e.jsxs("div",{className:"ask-hist",ref:n,children:[!r&&!s&&e.jsxs("div",{className:"warn-card",children:[e.jsx("div",{className:"warn-title",children:"Assist not running"}),e.jsx("div",{className:"warn-body",children:"Pi 5 with model weights + index required. Library search still available."})]}),f.length===0&&!x&&e.jsxs("div",{className:"empty",children:[e.jsx("div",{className:"empty-tag",style:{color:"var(--gn)"},children:"Library-Grounded Q&A"}),e.jsx("div",{children:"Answers are grounded in the offline Kiwix library. No internet required."}),e.jsx("div",{style:{marginTop:14,fontSize:12,color:"var(--mu)"},children:'Try: "how to purify water" · "treating burns" · "emergency shelter construction"'})]}),f.map((t,c)=>e.jsxs("div",{children:[e.jsx("div",{className:"msg-q",children:e.jsx("div",{className:"msg-q-text",children:t.q})}),e.jsxs("div",{className:"msg-a",children:[e.jsx("div",{className:`mode-badge ${t.r.mode}`,children:t.r.mode==="answer"?"✓ answer":t.r.mode==="defer"?"⚠ defer":t.r.mode==="error"?"✗ error":"— no answer"}),t.r.confidence!==void 0&&e.jsxs("div",{className:"conf",children:["CONFIDENCE: ",e.jsxs("span",{style:{color:t.r.confidence>.7?"var(--gn)":"var(--am)"},children:[(t.r.confidence*100).toFixed(0),"%"]})]}),e.jsx("div",{className:"ans-text",children:t.r.answer}),t.r.citations?.length>0&&e.jsxs("div",{className:"cites",children:[e.jsx("div",{style:{fontSize:10,color:"var(--mu)",fontFamily:"var(--ui)",fontWeight:700,letterSpacing:1.5,textTransform:"uppercase",marginBottom:3},children:"Sources"}),t.r.citations.map(g=>e.jsxs("div",{className:"cite-row",children:[e.jsxs("span",{className:"cite-n",children:["[",g.number,"]"]}),e.jsxs("span",{children:[g.article," → ",g.section]})]},g.number))]})]})]},c)),x&&e.jsxs("div",{className:"empty",children:[e.jsx(N,{}),e.jsx("div",{style:{marginTop:10,fontSize:12},children:"Querying library…"})]})]}),e.jsx("div",{className:"ask-bar",children:e.jsxs("div",{className:"ask-row",children:[e.jsx("textarea",{className:"ask-ta",value:l,onChange:t=>i(t.target.value),placeholder:"Ask the library…",rows:1,onKeyDown:t=>{t.key==="Enter"&&!t.shiftKey&&(t.preventDefault(),v())}}),e.jsx("button",{className:"btn-send",onClick:v,disabled:!l.trim()||x,children:e.jsx(j,{name:"send",size:17})})]})})]})}function E({podUrl:a,isDemo:s}){const[r,l]=o.useState(""),[i,x]=o.useState(!1),[m,f]=o.useState(null),h=async()=>{if(!(!r.trim()||i)){if(x(!0),s)await new Promise(n=>setTimeout(n,500)),f(u.retrieve);else try{const d=await(await fetch(`${a}/api/retrieve?q=${encodeURIComponent(r)}&k=8`,{signal:AbortSignal.timeout(1e4)})).json();f(d.results||[])}catch{f([])}x(!1)}};return e.jsxs("div",{className:"scr",children:[e.jsxs("div",{className:"srch-row",children:[e.jsx("input",{className:"srch-in",value:r,onChange:n=>l(n.target.value),placeholder:"Search the library…",onKeyDown:n=>n.key==="Enter"&&h()}),e.jsx("button",{className:"btn-p",onClick:h,disabled:!r.trim()||i,children:i?e.jsx(N,{}):"Go"})]}),m===null&&e.jsxs("div",{className:"empty",children:[e.jsx("div",{className:"empty-tag",style:{color:"var(--bl)"},children:"Knowledge Library"}),e.jsx("div",{children:"Wikipedia · iFixit · Survival guides · WikEM clinical · Regional maps — all offline."})]}),m?.length===0&&e.jsxs("div",{className:"empty",children:['No results for "',r,'"']}),m?.map((n,d)=>e.jsxs("a",{className:"res-row",href:a+n.url,target:"_blank",rel:"noopener noreferrer",children:[e.jsxs("div",{className:"res-sc",children:[(n.score*100).toFixed(0),"%"]}),e.jsxs("div",{children:[e.jsx("div",{className:"res-art",children:n.article}),e.jsxs("div",{className:"res-sec",children:["§ ",n.section]})]})]},d))]})}function $({podUrl:a,isDemo:s,listenReady:r}){const[l,i]=o.useState(u.presets),[x,m]=o.useState([]),[f,h]=o.useState(null),[n,d]=o.useState({freq_mhz:162.4,mode:"NFM",status:"idle"});o.useEffect(()=>{if(s){m(u.alerts);return}const t=async()=>{try{const[g,p,b]=await Promise.all([fetch(`${a}/api/listen/state`),fetch(`${a}/api/listen/alerts`),fetch(`${a}/api/listen/presets`)]);if(g.ok&&d(await g.json()),p.ok){const y=await p.json();m(y.alerts||[])}if(b.ok){const y=await b.json();i(y.presets||u.presets)}}catch{}};t();const c=setInterval(t,5e3);return()=>clearInterval(c)},[a,s]);const v=async t=>{if(h(t.label),s){d({freq_mhz:t.freq_mhz,mode:t.mode,status:"receiving"});return}try{await fetch(`${a}/api/listen/tune`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({freq_mhz:t.freq_mhz,mode:t.mode})})}catch{}};return e.jsxs("div",{className:"scr",children:[!r&&!s&&e.jsxs("div",{className:"warn-card",children:[e.jsx("div",{className:"warn-title",children:"Radio offline"}),e.jsx("div",{className:"warn-body",children:"RTL-SDR dongle (e.g. RTL-SDR Blog v4) not detected. Plug in a compatible USB SDR device and restart."})]}),e.jsxs("div",{className:"freq-disp",children:[e.jsx("div",{className:"freq-num",children:n.freq_mhz?.toFixed?.(3)??"162.400"}),e.jsx("div",{className:"freq-unit",children:"MHz"}),e.jsxs("div",{className:"freq-mode",children:[n.mode??"NFM"," · ",n.status??"idle"]})]}),e.jsx("div",{className:"sh",children:"Presets"}),e.jsx("div",{className:"preset-scroll",children:l.map(t=>e.jsx("button",{className:`chip ${f===t.label?"act":""}`,onClick:()=>v(t),children:t.label},t.label))}),e.jsx("div",{className:"sh",children:"Alerts"}),x.length===0&&e.jsx("div",{className:"card",style:{textAlign:"center",color:"var(--mu)",fontSize:12},children:"No active alerts"}),x.map((t,c)=>e.jsxs("div",{className:"alert-row",children:[e.jsxs("div",{className:"alert-type",children:[t.type," · ",S(t.ts)]}),e.jsxs("div",{className:"alert-text",children:[t.event,t.area?` — ${t.area}`:""]})]},c))]})}function q({podUrl:a,isDemo:s}){const[r,l]=o.useState([]),[i,x]=o.useState(""),[m,f]=o.useState(!1),[h,n]=o.useState(null),d=280,v=o.useCallback(async()=>{if(s){l(u.notes);return}try{const g=await(await fetch(`${a}/api/notes?limit=100`)).json();l(g.notes||[])}catch{}},[a,s]);o.useEffect(()=>{v()},[v]);const t=async()=>{if(!(!i.trim()||m||i.length>d)){if(f(!0),n(null),s){await new Promise(c=>setTimeout(c,400)),l(c=>[{id:`d${Date.now()}`,text:i.trim(),ts:Date.now()},...c]),x(""),f(!1);return}try{(await fetch(`${a}/api/notes`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:i.trim()})})).ok?(x(""),v()):n("Post rejected by pod.")}catch{n("Could not reach pod.")}f(!1)}};return e.jsxs("div",{className:"scr",children:[e.jsx("div",{className:"sh",children:"Post a note"}),e.jsx("textarea",{className:"note-ta",value:i,onChange:c=>x(c.target.value),placeholder:"Community info, resources, safety updates…",maxLength:d}),e.jsxs("div",{className:`char-ct ${i.length>d-40?"warn":""}`,children:[i.length," / ",d]}),h&&e.jsx("div",{style:{color:"var(--rd)",fontSize:12,marginBottom:8},children:h}),e.jsx("button",{className:"btn-p",style:{width:"100%",marginBottom:16},onClick:t,disabled:!i.trim()||m||i.length>d,children:m?"Posting…":"Post to Board"}),e.jsx("div",{className:"sh",children:"Board"}),r.length===0&&e.jsx("div",{className:"empty",children:"No notes yet. Be the first to post."}),r.map(c=>e.jsxs("div",{className:"note-card",children:[e.jsx("div",{className:"note-txt",children:c.text}),e.jsx("div",{className:"note-meta",children:S(c.ts)})]},c.id))]})}function D({podUrl:a,onSave:s,onClose:r,isDemo:l}){const[i,x]=o.useState(a);return e.jsx("div",{className:"overlay",onClick:r,children:e.jsxs("div",{className:"sheet",onClick:m=>m.stopPropagation(),children:[e.jsxs("div",{className:"modal-hdr",children:[e.jsx("div",{className:"modal-title",children:"⚙ Pod Settings"}),e.jsx("button",{className:"btn-ic",onClick:r,children:e.jsx(j,{name:"x",size:20})})]}),e.jsx("div",{className:"fld-lbl",children:"Pod Address"}),e.jsx("input",{className:"fld-in",value:i,onChange:m=>x(m.target.value),placeholder:"http://192.168.4.1"}),e.jsxs("div",{className:"fld-hint",children:["Join the ",e.jsx("strong",{style:{color:"var(--gn)"},children:"RPI-HUB-INFOHUB"})," Wi-Fi network first. The pod is always at ",e.jsx("code",{style:{color:"var(--gn)"},children:"http://192.168.4.1"})," or ",e.jsx("code",{style:{color:"var(--gn)"},children:"http://hub.local"}),". No internet required."]}),e.jsx("div",{className:"fld-lbl",children:"Current mode"}),e.jsx("div",{style:{fontSize:13,color:l?"var(--am)":"var(--gn)",fontFamily:"var(--mono)",padding:"8px 0 14px"},children:l?"◉ DEMO — mock data":"◉ LIVE — pod reachable"}),e.jsx("button",{className:"btn-full",onClick:()=>s(i.replace(/\/+$/,"")),children:"Connect"})]})})}function P(){const[a,s]=o.useState("status"),[r,l]=o.useState(M),[i,x]=o.useState(null),[m,f]=o.useState("demo"),[h,n]=o.useState(!1),[d,v]=o.useState(!0);o.useEffect(()=>{const p=typeof window<"u"?window.location.hostname:"";p==="192.168.4.1"||p==="hub.local"?(v(!1),l(""),f("online")):(v(!0),x(u.status),f("demo"))},[]),o.useEffect(()=>{if(d){x(u.status),f("demo");return}let p=!0;const b=async()=>{if(p)try{const w=await fetch(`${r}/api/status`,{signal:AbortSignal.timeout(4e3)});w.ok&&p&&(x(await w.json()),f("online"))}catch{p&&f(w=>w==="demo"?"demo":"offline")}};b();const y=setInterval(b,6e3);return()=>{p=!1,clearInterval(y)}},[r,d]);const t=i?.services||{},c={online:4,demo:2,connecting:1,offline:0}[m]??0,g=[{id:"status",label:"Status",icon:"home"},{id:"search",label:"Search",icon:"search"},{id:"ask",label:"Ask",icon:"chat"},{id:"radio",label:"Radio",icon:"antenna"},{id:"board",label:"Board",icon:"clipboard"}];return e.jsxs(e.Fragment,{children:[e.jsx("style",{children:F}),e.jsxs("div",{style:{display:"flex",flexDirection:"column",height:"100dvh",background:"var(--bg)"},children:[e.jsxs("div",{className:"hdr",children:[e.jsxs("div",{children:[e.jsx("div",{className:"logo",children:"rpi-hub"}),e.jsx("div",{className:"logo-sub",children:"OFFLINE INFOHUB"})]}),e.jsx("div",{style:{flex:1}}),e.jsxs("div",{style:{display:"flex",alignItems:"center",gap:8},children:[e.jsx("div",{className:"sig-bars",children:[1,2,3,4].map(p=>e.jsx("div",{className:`sig-bar${p<=c?" on":""}`},p))}),e.jsx("div",{className:`conn-lbl ${m}`,children:m})]}),e.jsx("button",{className:"btn-ic",onClick:()=>n(!0),children:e.jsx(j,{name:"settings",size:18})})]}),d&&e.jsxs("div",{className:"demo-baner",children:[e.jsx(j,{name:"wifi",size:14,color:"var(--am)"}),"DEMO — join RPI-HUB-INFOHUB Wi-Fi · tap ⚙ to connect"]}),a==="ask"?e.jsx("div",{style:{flex:1,overflow:"hidden",display:"flex",flexDirection:"column"},children:e.jsx(T,{podUrl:r,isDemo:d,assistReady:t.assist==="ready"})}):e.jsxs("div",{className:"main",children:[a==="status"&&e.jsx(B,{status:i}),a==="search"&&e.jsx(E,{podUrl:r,isDemo:d}),a==="radio"&&e.jsx($,{podUrl:r,isDemo:d,listenReady:t.listen==="ready"}),a==="board"&&e.jsx(q,{podUrl:r,isDemo:d})]}),e.jsx("div",{className:"bnav",children:g.map(p=>e.jsxs("button",{className:`nb${a===p.id?" act":""}`,onClick:()=>s(p.id),children:[e.jsx(j,{name:p.icon,size:21,color:a===p.id?"#4ade80":"#5a7a5a"}),p.label]},p.id))}),h&&e.jsx(D,{podUrl:r,isDemo:d,onSave:p=>{l(p),v(!1),f("connecting"),n(!1)},onClose:()=>n(!1)})]})]})}z.createRoot(document.getElementById("root")).render(e.jsx(o.StrictMode,{children:e.jsx(P,{})}));
