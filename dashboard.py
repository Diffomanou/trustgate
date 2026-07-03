"""

EN : TrustGate  dashboard — Robust.
     Two clearly separated modes:
       1. Built-in : tests the Day-4 Ambient Expense Agent (always available)
       2. Custom URL : the jury pastes their own agent's URL and tests it
"""

from __future__ import annotations
import sys, json, time, asyncio, logging, httpx
from typing import Callable

sys.path.insert(0, ".")

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

from src.trustgate.agents.recon_agent      import ReconAgent
from src.trustgate.agents.attack_generator import AttackGeneratorAgent
from src.trustgate.agents.executor_agent   import ExecutorAgent
from src.trustgate.agents.judge_agent      import JudgeAgent
from src.trustgate.agents.reporter_agent   import ReporterAgent
from src.trustgate.target.expense_agent    import process_expense as builtin_process

logging.basicConfig(level=logging.WARNING)
app = FastAPI(title="TrustGate")

# ──────────────────────────────────────────────────────────────────────────────
# EXTERNAL URL TARGET
# ──────────────────────────────────────────────────────────────────────────────

def make_url_target(url: str) -> Callable[[dict], dict]:
    """
   

    EN : Creates a target function that sends attacks to an external URL via
         HTTP POST. If the URL is unreachable or responds incorrectly, we
         return a structured error response instead of crashing the pipeline.
    """
    def call_external(request: dict) -> dict:
        try:
            resp = httpx.post(
                url,
                json=request,
                timeout=8.0,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            
            # EN : We normalise the response if expected keys are missing.
            return {
                "status":               data.get("status", "unknown"),
                "message":              data.get("message", str(data)),
                "human_review_required": data.get("human_review_required", False),
                "amount_usd":           data.get("amount_usd"),
            }
        except httpx.TimeoutException:
            return {
                "status":  "error",
                "message": f"Timeout — the agent at {url} did not respond within 8 seconds.",
                "human_review_required": False,
                "amount_usd": None,
            }
        except httpx.HTTPStatusError as e:
            return {
                "status":  "error",
                "message": f"HTTP {e.response.status_code} from {url}",
                "human_review_required": False,
                "amount_usd": None,
            }
        except Exception as exc:
            return {
                "status":  "error",
                "message": f"Connection failed: {exc}",
                "human_review_required": False,
                "amount_usd": None,
            }
    return call_external


# ──────────────────────────────────────────────────────────────────────────────
# HTML 
# ──────────────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TrustGate — AI Agent Security Tester</title>
<style>
/* ── DESIGN TOKENS ─────────────────────────────────────────────── */
:root{
  --bg:#0d1117;          /*  main background */
  --surface:#161b22;     /*  cards and panels */
  --border:#30363d;      /*  borders */
  --text:#e6edf3;        /*  main text */
  --muted:#8b949e;       /*  secondary text */
  --brand:#006494;       
  --accent:#e8622a;      /* accent orange */
  --pass:#3fb950;        /*  success green */
  --fail:#f85149;        /*  failure red */
  --warn:#d29922;        /*  warning yellow */
  --radius:8px;
  --shadow:0 2px 8px rgba(0,0,0,.3);
}

/* ── RESET & BASE ──────────────────────────────────────────────── */
*{box-sizing:border-box;margin:0;padding:0;}
body{
  background:var(--bg);
  color:var(--text);
  font-family:'Segoe UI',system-ui,sans-serif;
  font-size:14px;
  line-height:1.5;
  min-height:100vh;
  display:flex;
  flex-direction:column;
}

/* ── HEADER ────────────────────────────────────────────────────── */
/* Principle: clear identity, one primary action visible immediately */
header{
  background:var(--surface);
  border-bottom:1px solid var(--border);
  padding:14px 24px;
  display:flex;
  align-items:center;
  gap:16px;
  flex-shrink:0;
}
.logo{font-size:1.3rem;font-weight:700;color:var(--brand);white-space:nowrap;}
.logo span{color:var(--accent);}
.tagline{color:var(--muted);font-size:.8rem;flex:1;}
.badge-course{
  background:var(--brand);color:#fff;
  font-size:.7rem;padding:3px 10px;border-radius:20px;
  white-space:nowrap;
}

/* ── MAIN LAYOUT ───────────────────────────────────────────────── */
/* Principle: F-pattern — controls top-left, results centre-right */
.layout{
  display:grid;
  grid-template-columns:280px 1fr 300px;
  gap:0;
  flex:1;
  overflow:hidden;
  height:calc(100vh - 54px);
}

/* ── PANELS ────────────────────────────────────────────────────── */
.panel{
  overflow-y:auto;
  padding:16px;
  border-right:1px solid var(--border);
}
.panel:last-child{border-right:none;border-left:1px solid var(--border);}
.panel-title{
  font-size:.68rem;text-transform:uppercase;letter-spacing:1.2px;
  color:var(--muted);font-weight:600;
  margin-bottom:14px;
}

/* ── CARDS ─────────────────────────────────────────────────────── */
.card{
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:14px;
  margin-bottom:12px;
}
.card-title{
  font-size:.78rem;font-weight:600;color:var(--muted);
  text-transform:uppercase;letter-spacing:.8px;
  margin-bottom:10px;
}

/* ── TARGET SELECTOR ───────────────────────────────────────────── */
/* Principle: progressive disclosure — show URL field only when needed */
.mode-tabs{display:flex;gap:0;margin-bottom:14px;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;}
.mode-tab{
  flex:1;padding:9px 6px;text-align:center;font-size:.8rem;font-weight:600;
  cursor:pointer;background:transparent;color:var(--muted);
  border:none;transition:all .2s;
}
.mode-tab.active{background:var(--brand);color:#fff;}
.mode-tab:hover:not(.active){background:rgba(255,255,255,.05);}

.url-field{display:none;flex-direction:column;gap:6px;}
.url-field.visible{display:flex;}
.url-input{
  background:var(--bg);border:1px solid var(--border);border-radius:6px;
  padding:9px 12px;color:var(--text);font-size:.82rem;font-family:monospace;
  width:100%;outline:none;transition:border-color .2s;
}
.url-input:focus{border-color:var(--brand);}
.url-hint{font-size:.72rem;color:var(--muted);}
.url-hint code{color:var(--accent);font-size:.68rem;}

.url-status{
  font-size:.72rem;padding:5px 8px;border-radius:4px;
  display:none;align-items:center;gap:5px;
}
.url-status.checking{display:flex;color:var(--warn);background:rgba(210,153,34,.1);border:1px solid rgba(210,153,34,.2);}
.url-status.ok      {display:flex;color:var(--pass);background:rgba(63,185,80,.1); border:1px solid rgba(63,185,80,.2);}
.url-status.error   {display:flex;color:var(--fail);background:rgba(248,81,73,.1); border:1px solid rgba(248,81,73,.2);}

/* ── RUN BUTTON ────────────────────────────────────────────────── */
/* Principle: primary action is always visible and distinct */
.run-btn{
  width:100%;padding:12px;margin-bottom:14px;
  background:linear-gradient(135deg,var(--brand),var(--accent));
  color:#fff;font-size:.95rem;font-weight:700;border:none;
  border-radius:var(--radius);cursor:pointer;letter-spacing:.3px;
  transition:opacity .2s;display:flex;align-items:center;justify-content:center;gap:8px;
}
.run-btn:hover:not(:disabled){opacity:.88;}
.run-btn:disabled{opacity:.45;cursor:not-allowed;}

/* ── AGENT PIPELINE ─────────────────────────────────────────────── */
.agent-item{
  display:flex;align-items:center;gap:10px;
  padding:9px 10px;border:1px solid var(--border);border-radius:6px;
  margin-bottom:7px;transition:all .25s;
}
.agent-item.active{border-color:var(--accent);background:rgba(232,98,42,.07);}
.agent-item.done  {border-color:var(--pass);  background:rgba(63,185,80,.05);}
.agent-icon{font-size:1rem;width:24px;text-align:center;flex-shrink:0;}
.agent-info{flex:1;min-width:0;}
.agent-name{font-size:.82rem;font-weight:600;}
.agent-desc{font-size:.7rem;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.agent-dot{
  width:8px;height:8px;border-radius:50%;background:var(--border);
  flex-shrink:0;transition:background .3s;
}
.agent-item.active .agent-dot{background:var(--accent);animation:pulse 1s infinite;}
.agent-item.done   .agent-dot{background:var(--pass);}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* ── SCORE ──────────────────────────────────────────────────────── */
.score-display{text-align:center;padding:10px 0;}
.score-number{font-size:3.2rem;font-weight:800;color:var(--brand);line-height:1;}
.score-label {font-size:.72rem;color:var(--muted);margin-top:2px;}

.pillar-row{display:flex;align-items:center;gap:6px;margin-bottom:7px;}
.pillar-label{font-size:.7rem;color:var(--muted);min-width:110px;
              white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.pillar-track{flex:1;height:7px;background:var(--border);border-radius:4px;overflow:hidden;}
.pillar-fill {height:100%;border-radius:4px;transition:width 1s ease;
              background:linear-gradient(90deg,var(--brand),#00b4d8);}
.pillar-pct  {font-size:.7rem;font-weight:600;min-width:34px;text-align:right;}

/* ── TERMINAL ───────────────────────────────────────────────────── */
.term{
  background:#0a0d13;border:1px solid var(--border);border-radius:6px;
  padding:10px 12px;font-family:'Courier New',monospace;font-size:.75rem;
  max-height:150px;overflow-y:auto;margin-bottom:14px;
}
.t-dim   {color:var(--muted);}
.t-agent {color:var(--accent);font-weight:600;}
.t-info  {color:#58a6ff;}
.t-ok    {color:var(--pass);}
.t-fail  {color:var(--fail);}
.t-warn  {color:var(--warn);}

/* ── ATTACK CARDS ───────────────────────────────────────────────── */
/* Principle: each card tells a complete story — attack → response → verdict */
.attack-card{
  border:1px solid var(--border);border-radius:var(--radius);
  margin-bottom:10px;overflow:hidden;transition:border-color .3s;
}
.attack-card.pass{border-left:3px solid var(--pass);}
.attack-card.fail{border-left:3px solid var(--fail);}

.card-header{
  display:flex;align-items:center;gap:8px;
  padding:9px 12px;background:rgba(255,255,255,.02);
  border-bottom:1px solid var(--border);
}
.test-id    {font-family:monospace;font-size:.72rem;color:var(--accent);font-weight:700;min-width:54px;}
.test-name  {font-size:.82rem;font-weight:600;flex:1;min-width:0;
             white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.pillar-tag {font-size:.65rem;color:var(--muted);padding:2px 6px;
             background:var(--border);border-radius:10px;white-space:nowrap;}
.verdict    {font-size:.72rem;font-weight:700;padding:3px 9px;border-radius:10px;white-space:nowrap;}
.v-pass{background:rgba(63,185,80,.15); color:var(--pass);}
.v-fail{background:rgba(248,81,73,.15); color:var(--fail);}
.v-wait{background:var(--border);       color:var(--muted);}

.card-body{padding:10px 12px;}

/* ── MESSAGE BLOCKS ────────────────────────────────────────────── */
.msg-block{margin-bottom:8px;}
.msg-label{
  font-size:.63rem;font-weight:700;text-transform:uppercase;
  letter-spacing:1px;margin-bottom:3px;
}
.lbl-attack  {color:#58a6ff;}
.lbl-response{color:var(--pass);}
.lbl-verdict {color:var(--warn);}
.msg-body{
  background:rgba(255,255,255,.025);border:1px solid var(--border);
  border-radius:4px;padding:7px 9px;font-family:'Courier New',monospace;
  font-size:.75rem;white-space:pre-wrap;word-break:break-word;line-height:1.5;
}
.msg-body.attack-body   {border-color:rgba(88,166,255,.25);}
.msg-body.response-ok   {border-color:rgba(63,185,80,.25); color:var(--pass);}
.msg-body.response-fail {border-color:rgba(248,81,73,.25); color:var(--fail);}
.msg-body.response-warn {border-color:rgba(210,153,34,.25);color:var(--warn);}
.msg-body.verdict-body  {border-color:rgba(210,153,34,.2); color:#c9a227;}

.sev-tag{
  display:inline-block;font-size:.65rem;font-weight:700;
  padding:2px 6px;border-radius:3px;margin-top:4px;
}
.sev-low     {background:rgba(63,185,80,.15); color:var(--pass);}
.sev-medium  {background:rgba(210,153,34,.15);color:var(--warn);}
.sev-high    {background:rgba(248,81,73,.15); color:var(--fail);}
.sev-critical{background:rgba(248,81,73,.3);  color:var(--fail);}

/* ── RIGHT PANEL — REPORT ──────────────────────────────────────── */
.stat-row{
  display:flex;justify-content:space-between;align-items:center;
  padding:5px 0;border-bottom:1px solid var(--border);font-size:.8rem;
}
.stat-row:last-child{border-bottom:none;}
.stat-key{color:var(--muted);}

.finding-item{
  background:rgba(248,81,73,.06);border:1px solid rgba(248,81,73,.2);
  border-radius:6px;padding:9px;margin-bottom:6px;font-size:.75rem;
}
.finding-title{color:var(--fail);font-weight:600;margin-bottom:3px;}
.finding-fix  {color:var(--muted);font-size:.7rem;margin-top:4px;}

/* ── EMPTY STATE ───────────────────────────────────────────────── */
.empty{
  color:var(--muted);text-align:center;padding:32px 16px;
  font-size:.82rem;line-height:1.8;
}
.empty strong{color:var(--text);}

/* ── STATUS BAR ────────────────────────────────────────────────── */
footer{
  background:var(--surface);border-top:1px solid var(--border);
  padding:7px 20px;font-size:.75rem;color:var(--muted);
  display:flex;justify-content:space-between;align-items:center;flex-shrink:0;
}
#status{color:var(--accent);font-weight:600;}

/* ── TOOLTIP ───────────────────────────────────────────────────── */
[data-tip]{position:relative;cursor:help;}
[data-tip]:hover::after{
  content:attr(data-tip);position:absolute;bottom:120%;left:50%;
  transform:translateX(-50%);background:#000;color:#fff;
  font-size:.7rem;padding:4px 8px;border-radius:4px;
  white-space:nowrap;z-index:99;pointer-events:none;
}
</style>
</head>
<body>

<!-- ── HEADER ── -->
<header>
  <div class="logo">Trust<span>Gate</span> 🛡️</div>
  <p class="tagline">Adversarial Red-Teaming Pipeline for AI Agents</p>
  <span class="badge-course">Kaggle Capstone 2026</span>
</header>

<!-- ── LAYOUT ── -->
<div class="layout">

  <!-- LEFT PANEL : controls -->
  <div class="panel">

    <!-- Target selection -->
    <p class="panel-title">1 · Choose Target Agent</p>

    <div class="mode-tabs">
      <button class="mode-tab active" id="tab-builtin" onclick="setMode('builtin')">
        🏠 Built-in
      </button>
      <button class="mode-tab" id="tab-url" onclick="setMode('url')">
        🌐 Custom URL
      </button>
    </div>

    <!-- Built-in info -->
    <div id="info-builtin" class="card" style="margin-bottom:12px">
      <div class="card-title">Ambient Expense Agent</div>
      <p style="font-size:.76rem;color:var(--muted);line-height:1.6">
        The Day-4 codelab agent. Handles expense approvals with human-in-the-loop
        for amounts ≥ $100 and basic injection detection.
      </p>
      <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
        <span class="sev-tag sev-low">PII masking</span>
        <span class="sev-tag sev-low">Injection filter</span>
        <span class="sev-tag sev-low">HITL ≥ $100</span>
      </div>
    </div>

    <!-- Custom URL -->
    <div id="info-url" class="url-field">
      <label style="font-size:.76rem;color:var(--muted);font-weight:600">
        Your agent's endpoint URL
      </label>
      <input
        class="url-input"
        id="url-input"
        type="url"
        placeholder="https://your-agent.com/api/process"
        oninput="onUrlChange()"
      />
      <div class="url-status" id="url-status"></div>

      <label style="font-size:.76rem;color:var(--muted);font-weight:600;margin-top:10px;display:block">
        Describe your agent's role <span style="color:var(--accent)">*</span>
      </label>
      <textarea
        id="role-input"
        placeholder="e.g. HR assistant that answers questions about employee salaries and personal data"
        style="background:var(--bg);border:1px solid var(--border);border-radius:6px;
               padding:9px 12px;color:var(--text);font-size:.8rem;font-family:inherit;
               width:100%;resize:vertical;min-height:70px;outline:none;
               transition:border-color .2s;line-height:1.5;"
        onfocus="this.style.borderColor='var(--brand)'"
        onblur="this.style.borderColor='var(--border)'"
      ></textarea>
      <p class="url-hint">
        ✨ <strong style="color:var(--accent)">Gemini</strong> will generate 10 attacks
        tailored to your agent's domain.<br>
        Without a description, generic STRIDE payloads are used.<br><br>
        TrustGate POSTs: <code>{"content": "...", "role": "user"}</code><br>
        Expected: <code>status · message · human_review_required</code>
      </p>
    </div>

    <button class="run-btn" id="runBtn" onclick="runPipeline()">
      <span id="run-icon">▶</span>
      <span id="run-label">Run Red-Teaming Pipeline</span>
    </button>

    <!-- Agent pipeline -->
    <p class="panel-title">2 · Agent Pipeline</p>
    <div id="agents"></div>

    <!-- Score -->
    <div class="card">
      <div class="card-title">Trust Score</div>
      <div class="score-display">
        <div class="score-number" id="score">—</div>
        <div class="score-label">out of 100</div>
      </div>
      <div id="pillars" style="margin-top:10px"></div>
    </div>

  </div>

  <!-- CENTRE PANEL : live attack log -->
  <div class="panel">
    <p class="panel-title">3 · Live Attack Log — What the agents send & receive</p>

    <div class="term" id="term">
      <div class="t-dim">$ python dashboard.py</div>
      <div class="t-dim">Ready. Click "Run" to start.</div>
    </div>

    <div id="attacks">
      <div class="empty">
        <strong>Click "▶ Run Red-Teaming Pipeline"</strong><br>to start the security tests.<br><br>
        You will see every attack message sent to the agent<br>
        and the agent's exact response in real time.
      </div>
    </div>
  </div>

  <!-- RIGHT PANEL : report -->
  <div class="panel">
    <p class="panel-title">4 · Security Report</p>
    <div id="report">
      <div class="empty">
        Report will appear here<br>after the pipeline completes.
      </div>
    </div>
  </div>

</div>

<!-- STATUS BAR -->
<footer>
  <span>Status: <span id="status">Ready</span></span>
  <span id="elapsed"></span>
</footer>

<script>
// ── CONSTANTS ────────────────────────────────────────────────────
const AGENTS = [
  {id:"recon",    icon:"🔍", name:"ReconAgent",           desc:"Maps the attack surface"},
  {id:"gen",      icon:"📋", name:"AttackGeneratorAgent", desc:"Loads STRIDE test cases via MCP"},
  {id:"exec",     icon:"🚀", name:"ExecutorAgent",         desc:"Sends attacks to target (rate-limited)"},
  {id:"judge",    icon:"⚖️",  name:"JudgeAgent",           desc:"Evaluates each response"},
  {id:"reporter", icon:"📊", name:"ReporterAgent",         desc:"Computes scores & saves report"},
];
const PILLARS = [
  "spoofing","tampering","repudiation",
  "information_disclosure","denial_of_service","elevation_of_privilege"
];

let currentMode = "builtin";
let urlDebounce = null;

// ── MODE SWITCH ───────────────────────────────────────────────────
function setMode(mode) {
  currentMode = mode;
  document.getElementById("tab-builtin").className = "mode-tab" + (mode==="builtin"?" active":"");
  document.getElementById("tab-url").className     = "mode-tab" + (mode==="url"?" active":"");
  document.getElementById("info-builtin").style.display = mode==="builtin" ? "block" : "none";
  document.getElementById("info-url").className = "url-field" + (mode==="url"?" visible":"");
  clearUrlStatus();
}

// ── URL VALIDATION (debounced) ────────────────────────────────────
function onUrlChange() {
  clearTimeout(urlDebounce);
  const val = document.getElementById("url-input").value.trim();
  if (!val) { clearUrlStatus(); return; }

  // FR : On valide le format avant de contacter le serveur.
  // EN : We validate the format before contacting the server.
  try { new URL(val); } catch { showUrlStatus("error", "⚠ Invalid URL format"); return; }

  showUrlStatus("checking", "⏳ Checking reachability…");
  urlDebounce = setTimeout(() => checkUrl(val), 800);
}

async function checkUrl(url) {
  try {
    const r = await fetch("/check-url", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({url}),
    });
    const d = await r.json();
    if (d.ok) showUrlStatus("ok", "✓ Agent reachable — ready to test");
    else       showUrlStatus("error", "✗ " + d.error);
  } catch {
    showUrlStatus("error", "✗ Could not reach the URL");
  }
}

function showUrlStatus(cls, msg) {
  const el = document.getElementById("url-status");
  el.className = "url-status " + cls;
  el.textContent = msg;
}
function clearUrlStatus() {
  document.getElementById("url-status").className = "url-status";
}

// ── INIT ──────────────────────────────────────────────────────────
function initAgents() {
  document.getElementById("agents").innerHTML = AGENTS.map(a => `
    <div class="agent-item" id="ag-${a.id}">
      <div class="agent-icon">${a.icon}</div>
      <div class="agent-info">
        <div class="agent-name">${a.name}</div>
        <div class="agent-desc">${a.desc}</div>
      </div>
      <div class="agent-dot" id="dot-${a.id}"></div>
    </div>`).join("");
}

function initPillars() {
  document.getElementById("pillars").innerHTML = PILLARS.map(p => `
    <div class="pillar-row">
      <div class="pillar-label">${p.replace(/_/g," ")}</div>
      <div class="pillar-track"><div class="pillar-fill" id="pf-${p}" style="width:0%"></div></div>
      <div class="pillar-pct"  id="pp-${p}">—</div>
    </div>`).join("");
}

// ── HELPERS ───────────────────────────────────────────────────────
function setAgent(id, state) {
  document.getElementById("ag-"+id).className = "agent-item "+state;
}
function setStatus(t) { document.getElementById("status").textContent = t; }
function termLine(t, cls="t-dim") {
  const el = document.getElementById("term");
  const d  = document.createElement("div");
  d.className = cls; d.textContent = t;
  el.appendChild(d); el.scrollTop = el.scrollHeight;
}
function esc(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

// ── ATTACK CARDS ──────────────────────────────────────────────────
function addAttackCard(e) {
  const wrap = document.getElementById("attacks");
  if (wrap.querySelector(".empty")) wrap.innerHTML = "";
  const div = document.createElement("div");
  div.className = "attack-card"; div.id = "ac-"+e.test_id;
  div.innerHTML = `
    <div class="card-header">
      <span class="test-id">${e.test_id}</span>
      <span class="test-name" title="${esc(e.name)}">${esc(e.name)}</span>
      <span class="pillar-tag">${e.pillar.replace(/_/g," ")}</span>
      <span class="verdict v-wait" id="vd-${e.test_id}">…</span>
    </div>
    <div class="card-body">
      <div class="msg-block">
        <div class="msg-label lbl-attack">⚔️ Attack message sent to agent</div>
        <div class="msg-body attack-body">${esc(e.payload_content)}</div>
      </div>
      <div id="res-${e.test_id}"></div>
    </div>`;
  wrap.appendChild(div);
  div.scrollIntoView({behavior:"smooth", block:"nearest"});
}

function updateCard(e) {
  const card = document.getElementById("ac-"+e.test_id);
  if (!card) return;
  card.classList.add(e.passed ? "pass" : "fail");

  const vd = document.getElementById("vd-"+e.test_id);
  vd.className = "verdict " + (e.passed?"v-pass":"v-fail");
  vd.textContent = e.passed ? "✓ PASS" : "✗ FAIL";

  const r = e.response;
  const rClass = r.status==="rejected"?"response-fail":
                 r.status==="approved"&&e.passed?"response-ok":"response-warn";

  document.getElementById("res-"+e.test_id).innerHTML = `
    <div class="msg-block">
      <div class="msg-label lbl-response">💬 Agent response</div>
      <div class="msg-body ${rClass}">status               : ${esc(r.status||"—")}
message              : ${esc(r.message||"—")}
human_review_required: ${r.human_review_required?"YES ✓":"no"}
amount_usd           : ${r.amount_usd!=null?"$"+r.amount_usd:"N/A"}</div>
    </div>
    <div class="msg-block">
      <div class="msg-label lbl-verdict">⚖️ Judge verdict</div>
      <div class="msg-body verdict-body">${esc(e.explanation)}
<span class="sev-tag sev-${e.severity}">${e.severity.toUpperCase()}</span></div>
    </div>`;
}

// ── REPORT ────────────────────────────────────────────────────────
function renderReport(d) {
  const sc = d.overall_score;
  const scoreEl = document.getElementById("score");
  scoreEl.textContent = sc;
  scoreEl.style.color = sc>=90?"var(--pass)": sc>=70?"var(--warn)":"var(--fail)";

  const fails = d.findings.filter(f=>!f.passed);
  document.getElementById("report").innerHTML = `
    <div class="card">
      <div class="card-title">Summary</div>
      <div class="stat-row"><span class="stat-key">Target</span><span>${esc(d.target_name)}</span></div>
      <div class="stat-row"><span class="stat-key">Trust score</span>
        <span style="font-weight:700;color:${sc>=90?"var(--pass)":sc>=70?"var(--warn)":"var(--fail)"}">${sc}/100</span></div>
      <div class="stat-row"><span class="stat-key">Tests run</span><span>${d.findings.length}</span></div>
      <div class="stat-row"><span class="stat-key">Passed</span>
        <span style="color:var(--pass)">${d.findings.filter(f=>f.passed).length}</span></div>
      <div class="stat-row"><span class="stat-key">Failed</span>
        <span style="color:${fails.length>0?"var(--fail)":"var(--pass)"}">${fails.length}</span></div>
      <div class="stat-row"><span class="stat-key">Report saved</span>
        <span style="color:var(--muted);font-size:.7rem">reports/*.json</span></div>
    </div>
    <div class="card">
      <div class="card-title">STRIDE Scores</div>
      ${d.pillar_scores.filter(p=>p.total_tests>0).map(p=>`
      <div class="stat-row">
        <span class="stat-key" style="font-size:.75rem">${p.pillar.replace(/_/g," ")}</span>
        <span style="font-weight:700;color:${p.score>=80?"var(--pass)":"var(--warn)"}">${p.score}/100</span>
      </div>`).join("")}
    </div>
    ${fails.length>0 ? `
    <div class="card">
      <div class="card-title">⚠️ Vulnerabilities (${fails.length})</div>
      ${fails.map(f=>`
      <div class="finding-item">
        <div class="finding-title">${esc(f.test_id)} — ${esc(f.name)}</div>
        <div>${esc(f.explanation)}</div>
        ${f.remediation_hint?`<div class="finding-fix">✔ Fix: ${esc(f.remediation_hint)}</div>`:""}
      </div>`).join("")}
    </div>` : `
    <div class="card">
      <div class="card-title">✅ No vulnerabilities</div>
      <p style="color:var(--pass);font-size:.8rem;text-align:center;padding:6px">
        All ${d.findings.length} attacks resisted successfully.
      </p>
    </div>`}`;
}

// ── PIPELINE ──────────────────────────────────────────────────────
async function runPipeline() {
  // Validation
  if (currentMode === "url") {
    const url = document.getElementById("url-input").value.trim();
    if (!url) { setStatus("⚠ Please enter a URL first."); return; }
    try { new URL(url); } catch { setStatus("⚠ Invalid URL format."); return; }
  }

  const btn = document.getElementById("runBtn");
  btn.disabled = true;
  document.getElementById("run-icon").textContent  = "⏳";
  document.getElementById("run-label").textContent = "Running…";

  // Reset UI
  initAgents(); initPillars();
  document.getElementById("term").innerHTML =
    `<div class="t-agent">>>> TrustGate pipeline starting</div>`;
  document.getElementById("attacks").innerHTML = "";
  document.getElementById("report").innerHTML  =
    `<div class="empty">Waiting for pipeline…</div>`;
  document.getElementById("score").textContent = "—";
  document.getElementById("score").style.color = "var(--brand)";
  setStatus("Starting…");
  document.getElementById("elapsed").textContent = "";

  const t0 = Date.now();
  const agentRole = document.getElementById("role-input")
    ? document.getElementById("role-input").value.trim()
    : "";
  const params = currentMode === "url"
    ? "?target_url=" + encodeURIComponent(document.getElementById("url-input").value.trim())
      + (agentRole ? "&agent_role=" + encodeURIComponent(agentRole) : "")
    : "";

  const resp   = await fetch("/stream" + params);
  const reader = resp.body.getReader();
  const dec    = new TextDecoder();
  let buf = "";

  while(true) {
    const {done, value} = await reader.read();
    if(done) break;
    buf += dec.decode(value,{stream:true});
    const lines = buf.split("\n"); buf = lines.pop();
    for(const line of lines) {
      if(!line.startsWith("data:")) continue;
      try { handle(JSON.parse(line.slice(5).trim())); } catch{}
    }
  }

  document.getElementById("elapsed").textContent =
    "Completed in " + ((Date.now()-t0)/1000).toFixed(1) + "s";
  btn.disabled = false;
  document.getElementById("run-icon").textContent  = "▶";
  document.getElementById("run-label").textContent = "Run Again";
}

function handle(e) {
  switch(e.type) {
    case "agent_start":
      setAgent(e.id, "active");
      setStatus("Active: " + e.name);
      termLine(">>> " + e.name, "t-agent");
      break;
    case "agent_done":
      setAgent(e.id, "done");
      termLine("    ✓ done", "t-ok");
      break;
    case "log":
      termLine("    " + e.msg, "t-"+e.cls);
      break;
    case "attack_queued":
      addAttackCard(e);
      termLine("[→] " + e.test_id + " " + e.name, "t-info");
      break;
    case "attack_result":
      updateCard(e);
      termLine("[" + (e.passed?"✓":"✗") + "] " + e.test_id + " | " + e.severity, e.passed?"t-ok":"t-fail");
      break;
    case "pillar":
      document.getElementById("pf-"+e.pillar).style.width = e.score+"%";
      document.getElementById("pp-"+e.pillar).textContent = e.score+"/100";
      break;
    case "report":
      renderReport(e);
      setStatus("Done — Trust Score: " + e.overall_score + "/100 | " +
        e.findings.filter(f=>!f.passed).length + " vulnerability(ies) found");
      break;
  }
}

// Init on load
initAgents(); initPillars(); setMode("builtin");
</script>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.post("/check-url")
async def check_url(body: dict):
    """

    EN : Checks if a URL is reachable before launching the pipeline.
         We send a neutral message and verify we get a response.
    """
    url = body.get("url", "")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(url, json={"content": "ping", "role": "user"})
            return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


@app.get("/stream")
async def stream(target_url: str | None = None, agent_role: str | None = None):
    async def generate(target_url: str | None):
        def sse(data: dict) -> str:
            return f"data:{json.dumps(data, ensure_ascii=False)}\n\n"

       
        # EN : Picks the target function based on the selected mode.
        if target_url:
            target_fn = make_url_target(target_url)
            target_name = target_url
        else:
            target_fn = builtin_process
            target_name = "Ambient Expense Agent (Built-in)"

        context: dict = {
            "target_fn":  target_fn,
            "agent_role": agent_role.strip() if agent_role else "",
        }

        # ── RECON ──────────────────────────────────────────────────
        yield sse({"type":"agent_start","id":"recon","name":"ReconAgent"})
        ReconAgent().run(context)
        profile = context.get("target_profile", {})
        yield sse({"type":"log","msg":f"Target: {target_name}","cls":"info"})
        yield sse({"type":"log","msg":f"Guardrails: {len(profile.get('guardrails',[]))} detected","cls":"info"})
        yield sse({"type":"agent_done","id":"recon"})
        await asyncio.sleep(0.3)

        # ── ATTACK GENERATOR ───────────────────────────────────────
        yield sse({"type":"agent_start","id":"gen","name":"AttackGeneratorAgent"})
        AttackGeneratorAgent(use_mcp=False).run(context)
        tcs = context.get("test_cases", [])
        source = context.get("attack_source","")
        yield sse({"type":"log","msg":f"{len(tcs)} test cases — {source}","cls":"info"})
        for tc in tcs:
            yield sse({
                "type":            "attack_queued",
                "test_id":         tc.test_id,
                "name":            tc.name,
                "pillar":          tc.pillar.value,
                "payload_content": tc.payload.get("content", str(tc.payload)),
            })
        yield sse({"type":"agent_done","id":"gen"})
        await asyncio.sleep(0.2)

        # ── EXECUTOR ───────────────────────────────────────────────
        yield sse({"type":"agent_start","id":"exec","name":"ExecutorAgent"})
        ExecutorAgent(max_rps=3.0, target_fn=target_fn).run(context)
        yield sse({"type":"agent_done","id":"exec"})
        await asyncio.sleep(0.2)

        # ── JUDGE ──────────────────────────────────────────────────
        yield sse({"type":"agent_start","id":"judge","name":"JudgeAgent"})
        JudgeAgent().run(context)
        for f in context.get("findings", []):
            yield sse({
                "type":        "attack_result",
                "test_id":     f.trace.test_case.test_id,
                "name":        f.trace.test_case.name,
                "pillar":      f.trace.test_case.pillar.value,
                "passed":      f.passed,
                "severity":    f.severity.value,
                "explanation": f.explanation,
                "response":    f.trace.target_response,
            })
            await asyncio.sleep(0.18)
        yield sse({"type":"agent_done","id":"judge"})

        # ── REPORTER ───────────────────────────────────────────────
        yield sse({"type":"agent_start","id":"reporter","name":"ReporterAgent"})
        ReporterAgent().run(context)
        report = context.get("trust_report")
        if report:
            for ps in report.pillar_scores:
                if ps.total_tests > 0:
                    yield sse({"type":"pillar","pillar":ps.pillar.value,"score":ps.score_out_of_100})
                    await asyncio.sleep(0.12)
            yield sse({
                "type":          "report",
                "overall_score": report.overall_score,
                "target_name":   target_name,
                "generated_at":  report.generated_at,
                "pillar_scores": [
                    {"pillar":ps.pillar.value,"score":ps.score_out_of_100,
                     "total_tests":ps.total_tests,"passed_tests":ps.passed_tests}
                    for ps in report.pillar_scores if ps.total_tests > 0
                ],
                "findings": [
                    {"test_id":f.trace.test_case.test_id,"name":f.trace.test_case.name,
                     "passed":f.passed,"severity":f.severity.value,
                     "explanation":f.explanation,"remediation_hint":f.remediation_hint}
                    for f in report.findings
                ],
            })
        yield sse({"type":"agent_done","id":"reporter"})

    return StreamingResponse(
        generate(target_url),
        media_type="text/event-stream",
        headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"},
    )


if __name__ == "__main__":
    print("\n" + "="*58)
    print("  TrustGate Dashboard ")
    print("  http://localhost:8000")
    print("  Ctrl+C to stop")
    print("="*58 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
