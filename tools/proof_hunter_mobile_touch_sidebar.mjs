import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";

const targetUrl = process.env.HUNTER_REVIEW_URL;
if (!targetUrl) throw new Error("HUNTER_REVIEW_URL is required");
const outDir = process.env.PROOF_DIR || "artifacts/hunter-mobile-touch-sidebar";
await mkdir(outDir, { recursive: true });

const chromePath = [process.env.CHROME_PATH, "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium"].filter(Boolean).find(existsSync);
if (!chromePath) throw new Error("Chrome/Chromium not found");

const debugPort = 9231;
const chrome = spawn(chromePath, [
  "--headless=new",
  "--no-sandbox",
  "--disable-gpu",
  "--hide-scrollbars",
  `--remote-debugging-port=${debugPort}`,
  `--user-data-dir=${join(process.env.RUNNER_TEMP || "/tmp", `srg-hunter-touch-${Date.now()}`)}`,
  "--window-size=390,844",
  "about:blank",
], { stdio: ["ignore", "pipe", "pipe"] });

let log = "";
chrome.stdout.on("data", d => { log += String(d); });
chrome.stderr.on("data", d => { log += String(d); });
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function waitJson(url, attempts = 120) {
  for (let i = 0; i < attempts; i++) {
    try { const r = await fetch(url); if (r.ok) return r.json(); } catch {}
    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${url}\n${log.slice(-4000)}`);
}

let ws;
let seq = 0;
const pending = new Map();
function cdp(method, params = {}) {
  const id = ++seq;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
async function evalJs(expression) {
  const r = await cdp("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text || "Evaluation failed");
  return r.result?.value;
}
async function waitFor(expression, label, attempts = 100) {
  for (let i = 0; i < attempts; i++) {
    try { if (await evalJs(expression)) return; } catch {}
    await sleep(100);
  }
  throw new Error(`Timed out waiting for ${label}`);
}
async function point(selector) {
  return evalJs(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return null;const r=e.getBoundingClientRect();const x=r.left+r.width/2,y=r.top+r.height/2;const h=document.elementFromPoint(x,y);return{x,y,width:r.width,height:r.height,visible:getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'&&r.width>0&&r.height>0,hit:h===e||!!h?.closest?.(${JSON.stringify(selector)}),hitId:h?.id||'',hitClass:h?.className||''}})()`);
}
async function touch(selector) {
  const p = await point(selector);
  if (!p?.visible || !p.hit || p.width < 28 || p.height < 28) throw new Error(`Not a usable touch target: ${selector} ${JSON.stringify(p)}`);
  await cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: p.x, y: p.y, radiusX: 6, radiusY: 6, force: 1, id: 1 }] });
  await sleep(60);
  await cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await sleep(500);
  return p;
}
async function screenshot(name) {
  const r = await cdp("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false });
  await writeFile(join(outDir, name), Buffer.from(r.data, "base64"));
}
async function state(stage) {
  return evalJs(`(()=>{const s=document.querySelector('#sidebar'),d=document.querySelector('#drawerScrim'),m=document.querySelector('#mobileMenu');const sr=s?.getBoundingClientRect(),dr=d?.getBoundingClientRect();const cs=s?getComputedStyle(s):null,cd=d?getComputedStyle(d):null;const probe=sr?document.elementFromPoint(Math.min(120,sr.right-10),Math.min(150,sr.bottom-10)):null;return{stage:${JSON.stringify(stage)},ready:document.readyState,sidebarClass:s?.className||'',sidebarOpen:!!s?.classList.contains('open'),sidebarVisible:!!s&&cs.display!=='none'&&cs.visibility!=='hidden'&&Number(cs.opacity||1)>0&&sr.width>200&&sr.right>200,sidebarRect:sr?{left:sr.left,right:sr.right,width:sr.width,height:sr.height}:null,sidebarHit:!!probe?.closest?.('#sidebar'),scrimOpen:!!d?.classList.contains('open'),scrimVisible:!!d&&cd.display!=='none'&&cd.visibility!=='hidden'&&dr.width>0&&dr.height>0,menuExpanded:m?.getAttribute('aria-expanded')||'',htmlClass:document.documentElement.className,touchAudit:globalThis.__HUNTER_MOBILE_SIDEBAR_TOUCH_AUDIT__||null,marker:globalThis.__HUNTER_MOBILE_SIDEBAR_TOUCH_FIX_WIRED__||null}})()`);
}

const proof = { targetUrl, viewport: { width: 390, height: 844 }, input: "Input.dispatchTouchEvent touchStart/touchEnd", startedAt: new Date().toISOString(), stages: [] };
try {
  const tabs = await waitJson(`http://127.0.0.1:${debugPort}/json/list`);
  const target = tabs.find(t => t.type === "page") || tabs[0];
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.addEventListener("open", resolve, { once: true }); ws.addEventListener("error", reject, { once: true }); });
  ws.addEventListener("message", event => {
    const m = JSON.parse(String(event.data));
    if (!m.id || !pending.has(m.id)) return;
    const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result || {});
  });
  await cdp("Runtime.enable");
  await cdp("Page.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 3, mobile: true, screenWidth: 390, screenHeight: 844 });
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await cdp("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", platform: "iPhone" });
  await cdp("Page.navigate", { url: targetUrl });
  await waitFor("document.readyState==='complete'", "page load");
  await waitFor("!!document.querySelector('#mobileMenu')&&!!globalThis.__HUNTER_MOBILE_SIDEBAR__", "mobile sidebar runtime");
  await sleep(500);

  const before = await state("before-touch"); proof.stages.push(before); await screenshot("01-before-touch.png");
  const targetPoint = await touch("#mobileMenu"); proof.targetPoint = targetPoint;
  const after = await state("after-touch"); proof.stages.push(after); await screenshot("02-after-touch.png");

  const failures = [];
  if (!after.sidebarOpen) failures.push("sidebar lacks open class after real touch");
  if (!after.sidebarVisible) failures.push("sidebar is not visibly rendered after real touch");
  if (!after.sidebarHit) failures.push("sidebar is not the topmost layer inside its visible area");
  if (!after.scrimOpen || !after.scrimVisible) failures.push("drawer scrim is not open and visible");
  if (after.menuExpanded !== "true") failures.push("menu aria-expanded is not true");
  if (failures.length) throw new Error(`${failures.join("; ")}\n${JSON.stringify(after, null, 2)}`);

  proof.passed = true;
  proof.completedAt = new Date().toISOString();
  await writeFile(join(outDir, "proof.json"), JSON.stringify(proof, null, 2));
  console.log("SRG TOUCH PASS: a real mobile touch opens a visible, topmost Hunter sidebar.");
} catch (error) {
  proof.passed = false;
  proof.error = String(error?.stack || error);
  proof.completedAt = new Date().toISOString();
  await writeFile(join(outDir, "proof.json"), JSON.stringify(proof, null, 2));
  try { await screenshot("99-failure.png"); } catch {}
  throw error;
} finally {
  try { ws?.close(); } catch {}
  chrome.kill("SIGTERM");
  await sleep(250);
  if (!chrome.killed) chrome.kill("SIGKILL");
}
