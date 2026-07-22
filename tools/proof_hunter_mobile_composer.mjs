import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";

const targetUrl = process.env.HUNTER_REVIEW_URL;
if (!targetUrl) throw new Error("HUNTER_REVIEW_URL is required");
const outDir = process.env.PROOF_DIR || "artifacts/hunter-mobile-composer";
await mkdir(outDir, { recursive: true });

const chromePath = [process.env.CHROME_PATH, "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium"].filter(Boolean).find(existsSync);
if (!chromePath) throw new Error("Chrome/Chromium not found");

const debugPort = 9237;
const chrome = spawn(chromePath, [
  "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
  `--remote-debugging-port=${debugPort}`,
  `--user-data-dir=${join(process.env.RUNNER_TEMP || "/tmp", `srg-hunter-composer-${Date.now()}`)}`,
  "--window-size=390,844", "about:blank",
], { stdio: ["ignore", "pipe", "pipe"] });
let log = "";
chrome.stdout.on("data", d => { log += String(d); });
chrome.stderr.on("data", d => { log += String(d); });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitJson(url, attempts = 120) { for (let i = 0; i < attempts; i++) { try { const r = await fetch(url); if (r.ok) return r.json(); } catch {} await sleep(250); } throw new Error(`Timed out waiting for ${url}\n${log.slice(-4000)}`); }
let ws; let seq = 0; const pending = new Map();
function cdp(method, params = {}) { const id = ++seq; return new Promise((resolve, reject) => { pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); }); }
async function evalJs(expression) { const r = await cdp("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text || "Evaluation failed"); return r.result?.value; }
async function waitFor(expression, label, attempts = 120) { for (let i = 0; i < attempts; i++) { try { if (await evalJs(expression)) return; } catch {} await sleep(100); } throw new Error(`Timed out waiting for ${label}`); }
async function point(selector) { return evalJs(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return null;const r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2,h=document.elementFromPoint(x,y);return{x,y,width:r.width,height:r.height,visible:getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'&&r.width>0&&r.height>0,hit:h===e||!!h?.closest?.(${JSON.stringify(selector)}),hitId:h?.id||'',hitClass:h?.className||''}})()`); }
async function touch(selector, settle = 120) { const p = await point(selector); if (!p?.visible || !p.hit || p.width < 28 || p.height < 28) throw new Error(`Not a usable touch target: ${selector} ${JSON.stringify(p)}`); await cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: p.x, y: p.y, radiusX: 6, radiusY: 6, force: 1, id: 1 }] }); await sleep(45); await cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await sleep(settle); return p; }
async function screenshot(name) { const r = await cdp("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false }); await writeFile(join(outDir, name), Buffer.from(r.data, "base64")); }
async function state(stage) { return evalJs(`(()=>{const i=document.querySelector('#hcs2Input'),a=globalThis.__HUNTER_CHAT_COMPOSER_RELIABILITY_AUDIT__;return{stage:${JSON.stringify(stage)},activeId:document.activeElement?.id||'',activeTag:document.activeElement?.tagName||'',input:i?.value||'',inputDisabled:!!i?.disabled,inputReadOnly:!!i?.readOnly,inputConnected:!!i?.isConnected,inputToken:globalThis.__SRG_COMPOSER_NODE_TOKEN__?.get?.(i)||0,inputRect:i?(()=>{const r=i.getBoundingClientRect();return{left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}})():null,userMessages:document.querySelectorAll('.hcs2-row.user').length,hunterMessages:document.querySelectorAll('.hcs2-row.hunter').length,voiceLayer:!!document.querySelector('#hunterVoiceLayer'),voiceLabel:document.querySelector('#hcs2Voice')?.getAttribute('aria-label')||'',toast:document.querySelector('#hunterNativeDictationToast')?.textContent||'',trace:(globalThis.__SRG_COMPOSER_TRACE__||[]).slice(-60),audit:a||null}})()`); }

const proof = { targetUrl, viewport: { width: 390, height: 844 }, inputMode: "real touch plus CDP keyboard insertion", stages: [], startedAt: new Date().toISOString() };
try {
  const tabs = await waitJson(`http://127.0.0.1:${debugPort}/json/list`);
  const target = tabs.find(t => t.type === "page") || tabs[0];
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { ws.addEventListener("open", resolve, { once: true }); ws.addEventListener("error", reject, { once: true }); });
  ws.addEventListener("message", event => { const m = JSON.parse(String(event.data)); if (!m.id || !pending.has(m.id)) return; const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(JSON.stringify(m.error))) : p.resolve(m.result || {}); });
  await cdp("Runtime.enable"); await cdp("Page.enable");
  await cdp("Page.addScriptToEvaluateOnNewDocument", { source: `
    globalThis.__SRG_COMPOSER_TRACE__=[];
    globalThis.__SRG_COMPOSER_NODE_TOKEN__=new WeakMap();
    let __srgToken=0;
    const token=node=>{if(!node)return 0;if(!globalThis.__SRG_COMPOSER_NODE_TOKEN__.has(node))globalThis.__SRG_COMPOSER_NODE_TOKEN__.set(node,++__srgToken);return globalThis.__SRG_COMPOSER_NODE_TOKEN__.get(node)};
    const record=(type,event)=>{const target=event?.target,active=document.activeElement,input=document.querySelector('#hcs2Input');globalThis.__SRG_COMPOSER_TRACE__.push({type,targetId:target?.id||'',targetTag:target?.tagName||'',targetToken:token(target),inputToken:token(input),activeId:active?.id||'',activeTag:active?.tagName||'',activeToken:token(active),defaultPrevented:!!event?.defaultPrevented,trusted:!!event?.isTrusted,at:performance.now()});if(globalThis.__SRG_COMPOSER_TRACE__.length>160)globalThis.__SRG_COMPOSER_TRACE__.shift()};
    ['touchstart','touchend','pointerdown','pointerup','mousedown','mouseup','click','focus','focusin','blur','focusout','beforeinput','input'].forEach(type=>document.addEventListener(type,event=>record(type,event),true));
    new MutationObserver(()=>{const input=document.querySelector('#hcs2Input');if(input)record('mutation-input-present',{target:input,isTrusted:false,defaultPrevented:false})}).observe(document.documentElement,{subtree:true,childList:true});
  ` });
  await cdp("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 3, mobile: true, screenWidth: 390, screenHeight: 844 });
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
  await cdp("Emulation.setUserAgentOverride", { userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", platform: "iPhone" });
  await cdp("Page.navigate", { url: targetUrl });
  await waitFor("document.readyState==='complete'&&!!globalThis.__HUNTER_MOBILE_SIDEBAR__", "Hunter mobile runtime");
  await touch("#mobileMenu", 100);
  await waitFor("document.querySelector('#sidebar')?.classList.contains('open')", "sidebar open");
  const chatSelector = await evalJs(`(()=>{const b=[...document.querySelectorAll('#sidebar button,#sidebar a')].find(x=>/Talk to Hunter/i.test((x.textContent||'').replace(/\\s+/g,' ').trim()));if(!b)return null;b.dataset.srgComposerChat='true';return '#sidebar [data-srg-composer-chat="true"]'})()`);
  if (!chatSelector) throw new Error("Talk to Hunter was not available.");
  await touch(chatSelector, 200);
  await waitFor("document.querySelector('#page-hunter-chat')?.classList.contains('active')&&!!document.querySelector('#hcs2Input')&&!!globalThis.__HUNTER_CHAT_COMPOSER_RELIABILITY__", "reliable Hunter composer");

  const ready = await state("composer-ready"); proof.stages.push(ready);
  if (!ready.audit?.passed) throw new Error(`Composer audit failed before typing: ${JSON.stringify(ready.audit)}`);
  if (ready.inputDisabled || ready.inputReadOnly || ready.inputRect?.width < 80) throw new Error(`Composer is not usable: ${JSON.stringify(ready)}`);
  await screenshot("01-composer-ready.png");

  await evalJs("globalThis.__SRG_COMPOSER_TRACE__=[]");
  await touch("#hcs2Input", 500);
  const touched = await state("after-textarea-touch"); proof.stages.push(touched);
  await screenshot("02-after-textarea-touch.png");
  if (touched.activeId !== "hcs2Input") throw new Error(`Textarea did not retain focus after touch: ${JSON.stringify(touched,null,2)}`);
  await cdp("Input.insertText", { text: "hello from the phone keyboard" });
  await waitFor("document.querySelector('#hcs2Input')?.value==='hello from the phone keyboard'", "keyboard text in textarea");
  const typed = await state("typed"); proof.stages.push(typed);
  if (typed.activeId !== "hcs2Input") throw new Error(`Textarea lost focus while typing: ${JSON.stringify(typed)}`);
  await screenshot("03-real-keyboard-text.png");

  const baselineUsers = typed.userMessages, baselineHunters = typed.hunterMessages;
  await touch("#hcs2Send", 240);
  await waitFor(`document.querySelectorAll('.hcs2-row.user').length===${baselineUsers + 1}`, "typed message send");
  await waitFor(`document.querySelectorAll('.hcs2-row.hunter').length>${baselineHunters}`, "Hunter reply to typed message");
  const sent = await state("typed-message-sent"); proof.stages.push(sent);
  await screenshot("04-typed-message-sent.png");

  await touch("#hcs2Voice", 140);
  await waitFor("document.activeElement?.id==='hcs2Input'&&!!document.querySelector('#hunterNativeDictationToast')", "native keyboard dictation fallback");
  const fallback = await state("ios-native-dictation"); proof.stages.push(fallback);
  if (fallback.voiceLayer) throw new Error("Voice opened the unsupported browser popup instead of native keyboard dictation.");
  if (!/Dictate message/i.test(fallback.voiceLabel)) throw new Error(`Voice button does not expose native dictation: ${fallback.voiceLabel}`);
  if (!/microphone on your keyboard/i.test(fallback.toast)) throw new Error(`Native dictation guidance is missing: ${fallback.toast}`);
  if (!fallback.audit?.lastVoiceFallback?.focused) throw new Error(`Native dictation did not focus the composer: ${JSON.stringify(fallback.audit)}`);
  await screenshot("05-native-keyboard-dictation.png");

  proof.passed = true; proof.completedAt = new Date().toISOString();
  await writeFile(join(outDir, "proof.json"), JSON.stringify(proof, null, 2));
  console.log("SRG COMPOSER PASS: the phone textarea receives real keyboard input, sends normally, and iPhone Voice uses native keyboard dictation without a dead popup.");
} catch (error) {
  proof.passed = false; proof.error = String(error?.stack || error); proof.completedAt = new Date().toISOString();
  await writeFile(join(outDir, "proof.json"), JSON.stringify(proof, null, 2));
  try { await screenshot("99-failure.png"); } catch {}
  throw error;
} finally {
  try { ws?.close(); } catch {}
  chrome.kill("SIGTERM"); await sleep(250); if (!chrome.killed) chrome.kill("SIGKILL");
}
