"""The phone-facing web app: one push-to-talk button, served by susurrate itself.

Served at GET /. Needs a secure context (HTTPS or localhost) for microphone
access — put `tailscale serve` in front for phones.
"""

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<title>susurrate</title>
<style>
  :root { color-scheme: dark; }
  * { margin: 0; box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  body {
    font: 17px/1.45 -apple-system, system-ui, sans-serif;
    background: #0d1117; color: #e6edf3;
    min-height: 100dvh; display: flex; flex-direction: column;
    padding: max(env(safe-area-inset-top), 16px) 20px max(env(safe-area-inset-bottom), 16px);
  }
  header { display: flex; justify-content: space-between; align-items: center; }
  h1 { font-size: 20px; font-weight: 650; letter-spacing: .3px; }
  .mode { display: flex; gap: 4px; background: #161b22; border-radius: 10px; padding: 4px; }
  .mode button {
    border: 0; background: transparent; color: #8b949e; font: inherit;
    font-size: 14px; padding: 6px 14px; border-radius: 7px;
  }
  .mode button.on { background: #238636; color: #fff; }
  main { flex: 1; display: flex; flex-direction: column; gap: 14px; padding-top: 18px; }
  #out {
    flex: 1; background: #161b22; border-radius: 14px; padding: 14px;
    white-space: pre-wrap; overflow-y: auto; font-size: 16px; min-height: 120px;
  }
  #out .dim { color: #8b949e; }
  #status { text-align: center; color: #8b949e; font-size: 14px; min-height: 20px; }
  #talk {
    border: 0; border-radius: 50%; width: 132px; height: 132px; align-self: center;
    background: #21262d; color: #e6edf3; font: inherit; font-size: 15px; font-weight: 600;
    box-shadow: inset 0 0 0 2px #30363d;
  }
  #talk.rec { background: #da3633; box-shadow: 0 0 0 8px rgba(218,54,51,.25); }
  #copy {
    border: 0; border-radius: 10px; padding: 12px; font: inherit; font-weight: 600;
    background: #21262d; color: #e6edf3;
  }
</style>
</head>
<body>
<header>
  <h1>susurrate</h1>
  <div class="mode">
    <button id="m-dictate" class="on">Dictate</button>
    <button id="m-ask">Ask</button>
  </div>
</header>
<main>
  <div id="out"><span class="dim">Tap the button, speak, tap again.</span></div>
  <div id="status"></div>
  <button id="talk">talk</button>
  <button id="copy" hidden>Copy</button>
</main>
<script>
const $ = id => document.getElementById(id);
let mode = "dictate", rec = null, chunks = [], busy = false;

function token(force) {
  let t = localStorage.token;
  if (!t || force) {
    t = prompt("susurrate token (from the server's token file):") || "";
    localStorage.token = t.trim();
  }
  return localStorage.token;
}

function setMode(m) {
  mode = m;
  $("m-dictate").classList.toggle("on", m === "dictate");
  $("m-ask").classList.toggle("on", m === "ask");
}
$("m-dictate").onclick = () => setMode("dictate");
$("m-ask").onclick = () => setMode("ask");

$("talk").onclick = async () => {
  if (busy) return;
  if (rec) { rec.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    rec = new MediaRecorder(stream);
    chunks = [];
    rec.ondataavailable = e => chunks.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(chunks, { type: rec.mimeType });
      rec = null;
      $("talk").classList.remove("rec");
      $("talk").textContent = "talk";
      send(blob);
    };
    rec.start();
    $("talk").classList.add("rec");
    $("talk").textContent = "stop";
    $("status").textContent = "listening\\u2026";
  } catch (e) {
    $("status").textContent = "mic blocked: " + e.message;
  }
};

async function send(blob) {
  busy = true;
  $("status").textContent = mode === "ask" ? "thinking\\u2026" : "transcribing\\u2026";
  const url = mode === "ask" ? "/agent?llm=0&continue=1" : "/dictate?llm=1";
  try {
    const resp = await fetch(url, {
      method: "POST",
      headers: { Authorization: "Bearer " + token() },
      body: blob,
    });
    if (resp.status === 401) { token(true); busy = false; $("status").textContent = "token updated \\u2014 try again"; return; }
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.error || resp.status);
    const text = mode === "ask" ? data.reply : data.text;
    $("out").textContent = text || "(empty)";
    $("copy").hidden = !text;
    $("status").textContent = "";
    if (text && navigator.clipboard) navigator.clipboard.writeText(text).catch(() => {});
    if (mode === "ask" && text && "speechSynthesis" in window) {
      speechSynthesis.cancel();
      speechSynthesis.speak(new SpeechSynthesisUtterance(text));
    }
  } catch (e) {
    $("status").textContent = "error: " + e.message;
  }
  busy = false;
}

$("copy").onclick = () => {
  navigator.clipboard.writeText($("out").textContent);
  $("status").textContent = "copied";
};
</script>
</body>
</html>
"""
