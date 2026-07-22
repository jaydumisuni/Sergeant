import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";

const targetUrl = process.env.HUNTER_REVIEW_URL;
if (!targetUrl) throw new Error("HUNTER_REVIEW_URL is required");
const outDir = process.env.PROOF_DIR || "artifacts/hunter-full-standard";
await mkdir(outDir, { recursive: true });
const chromePath = [process.env.CHROME_PATH, "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium"].filter(Boolean).find(existsSync);
if (!chromePath) throw new Error("Chrome/Chromium not found");

const debugPort = 9247;
const chrome = spawn(chromePath, [
  "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", "--disable-background-networking",
  `--remote-debugging-port=${debugPort}`,
  `--user-data-dir=${join(process.env.RUNNER_TEMP || "/tmp", `srg-hunter-standard-v2-${Date.now()}`)}`,
  "--window-size=1920,1080", "about:blank",
], { stdio: ["ignore", "pipe", "pipe"] });
let browserLog = "";
chrome.stdout.on("data", d => { browserLog += String(d); });
chrome.stderr.on("data", d => { browserLog += String(d); });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitJson(url, attempts = 160) { for (let i = 0; i < attempts; i++) { try { const r = await fetch(url); if (r.ok) return r.json(); } catch {} await sleep(250); } throw new Error(`Chrome unavailable\n${browserLog.slice(-5000)}`); }

let ws, seq = 0;
const pending = new Map();
const runtimeErrors = [], consoleErrors = [], networkFailures = [], unsafeRequests = [];
function cdp(method, params = {}) { const id = ++seq; return new Promise((resolve, reject) => { pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); }); }
async function evalJs(expression) { const r = await cdp("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text || "Evaluation failed"); return r.result?.value; }
async function waitFor(expression, label, attempts = 140, delay = 90) { for (let i = 0; i < attempts; i++) { try { if (await evalJs(expression)) return; } catch {} await sleep(delay); } throw new Error(`Timed out waiting for ${label}`); }
async function screenshot(name) { const r = await cdp("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false }); await writeFile(join(outDir, name), Buffer.from(r.data, "base64")); }

const profiles = [
  { name: "mobile-390x844", width: 390, height: 844, mobile: true, ua: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1", platform: "iPhone" },
  { name: "desktop-1440x900", width: 1440, height: 900, mobile: false, ua: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36", platform: "Linux x86_64" },
  { name: "wide-1920x1080", width: 1920, height: 1080, mobile: false, ua: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36", platform: "Linux x86_64" },
];
async function configure(p) {
  await cdp("Emulation.setDeviceMetricsOverride", { width: p.width, height: p.height, deviceScaleFactor: p.mobile ? 3 : 1, mobile: p.mobile, screenWidth: p.width, screenHeight: p.height });
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: p.mobile, maxTouchPoints: p.mobile ? 5 : 0 });
  await cdp("Emulation.setUserAgentOverride", { userAgent: p.ua, platform: p.platform });
}
async function navigate(p, suffix = "") {
  await configure(p);
  const sep = targetUrl.includes("?") ? "&" : "?";
  await cdp("Page.navigate", { url: `${targetUrl}${sep}srg-standard-v2=${Date.now()}${suffix}` });
  await waitFor("document.readyState==='complete'&&!!document.querySelector('#sidebar')&&!!document.querySelector('#roleSelect')", `${p.name} shell`);
  await sleep(320);
}
async function setRole(role) {
  const ok = await evalJs(`(()=>{const s=document.querySelector('#roleSelect');if(!s||![...s.options].some(o=>o.value===${JSON.stringify(role)}))return false;s.value=${JSON.stringify(role)};s.dispatchEvent(new Event('change',{bubbles:true}));return true})()`);
  if (!ok) throw new Error(`Role unavailable: ${role}`);
  await sleep(380);
}
async function shell() {
  return evalJs(`(()=>{const a=document.querySelector('.page.active'),s=document.querySelector('#sidebar'),d=document.querySelector('#drawerScrim'),m=document.querySelector('#modal');return{page:a?.id||'',title:a?.querySelector('h1,h2')?.textContent?.replace(/\s+/g,' ').trim()||'',drawer:!!s?.classList.contains('open'),scrim:!!d?.classList.contains('open'),modal:!!m?.classList.contains('open'),modalTitle:document.querySelector('#modalTitle')?.textContent?.trim()||'',chat:!!document.querySelector('#page-hunter-chat')?.classList.contains('active'),overflow:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)-innerWidth,role:document.querySelector('#roleSelect')?.value||'',guard:globalThis.__HUNTER_FULL_STANDARD_GUARD_AUDIT__||null,sidebarAudit:globalThis.__HUNTER_MOBILE_SIDEBAR_TOUCH_AUDIT__||null}})()`);
}
async function point(selector) {
  return evalJs(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return null;e.scrollIntoView({block:'center',inline:'center'});const r=e.getBoundingClientRect(),x=Math.max(1,Math.min(innerWidth-2,r.left+r.width/2)),y=Math.max(1,Math.min(innerHeight-2,r.top+r.height/2)),h=document.elementFromPoint(x,y),s=getComputedStyle(e);return{x,y,width:r.width,height:r.height,visible:s.display!=='none'&&s.visibility!=='hidden'&&Number(s.opacity||1)>0&&r.width>0&&r.height>0,hit:h===e||e.contains(h)||!!h?.closest?.(${JSON.stringify(selector)}),disabled:!!e.disabled||e.getAttribute('aria-disabled')==='true',hitId:h?.id||'',label:(e.getAttribute('aria-label')||e.title||e.textContent||'').replace(/\s+/g,' ').trim()}})()`);
}
async function activate(selector, p, settle = 360) {
  const v = await point(selector);
  if (!v?.visible || v.disabled || !v.hit || v.width < 24 || v.height < 24) throw new Error(`Unusable control ${selector}: ${JSON.stringify(v)}`);
  if (p.mobile) {
    await cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: v.x, y: v.y, radiusX: 7, radiusY: 7, force: 1, id: 1 }] });
    await sleep(55);
    await cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  } else {
    await cdp("Input.dispatchMouseEvent", { type: "mousePressed", x: v.x, y: v.y, button: "left", clickCount: 1 });
    await sleep(25);
    await cdp("Input.dispatchMouseEvent", { type: "mouseReleased", x: v.x, y: v.y, button: "left", clickCount: 1 });
  }
  await sleep(settle);
}
async function visibleMenuSelector() {
  return evalJs(`(()=>{for(const s of ['#hcs2Menu','#mobileMenu']){const e=document.querySelector(s);if(!e)continue;const r=e.getBoundingClientRect(),c=getComputedStyle(e);if(c.display!=='none'&&c.visibility!=='hidden'&&r.width>=24&&r.height>=24)return s}return''})()`);
}
async function openDrawer(p) {
  const selector = await visibleMenuSelector();
  if (!selector) throw new Error(`${p.name}: no visible mobile menu control`);
  await activate(selector, p, 300);
  await waitFor("document.querySelector('#sidebar')?.classList.contains('open')", `${p.name} drawer open`, 100, 70);
  const st = await shell();
  if (!st.scrim) throw new Error(`${p.name}: drawer opened without scrim through ${selector}`);
  return selector;
}
async function closeDrawer(p) {
  const closeVisible = await evalJs(`(()=>{const e=document.querySelector('#hunterMobileSidebarClose');if(!e)return false;const r=e.getBoundingClientRect(),s=getComputedStyle(e);return s.display!=='none'&&r.width>=24&&r.height>=24})()`);
  await activate(closeVisible ? "#hunterMobileSidebarClose" : "#drawerScrim", p, 220);
  await waitFor("!document.querySelector('#sidebar')?.classList.contains('open')&&!document.querySelector('#drawerScrim')?.classList.contains('open')", `${p.name} drawer close`, 100, 70);
}
async function roles() { return evalJs("[...document.querySelector('#roleSelect').options].map(o=>o.value)"); }
async function navItems(p) {
  if (p.mobile) await openDrawer(p);
  const items = await evalJs(`(()=>{const vis=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&r.width>0&&r.height>0};const all=[...document.querySelectorAll('#nav button,#nav a,#hunterUnifiedChatNav button,#sidebar [data-view],#sidebar [data-hunter-custom],#sidebar [data-business-custom],#sidebar [data-role-accountability-route],#sidebar [data-family-tracking],#sidebar [data-unified-chat],#sidebar [data-unified-project],#sidebar [data-ops-custom]')].filter((e,i,a)=>a.indexOf(e)===i).filter(vis).filter(e=>e.id!=='hunterMobileSidebarClose'&&!e.closest('.account-zone'));const keys=['data-view','data-hunter-custom','data-business-custom','data-role-accountability-route','data-family-tracking','data-unified-chat','data-unified-project','data-ops-custom'];return all.map((e,i)=>{const pair=keys.map(k=>[k,e.getAttribute(k)]).find(x=>x[1]);return{id:e.id||'',attr:pair?.[0]||'',value:pair?.[1]||'',label:(e.getAttribute('aria-label')||e.title||e.textContent||'').replace(/\s+/g,' ').trim(),active:e.classList.contains('active'),i}}).filter(x=>x.id||x.attr)})()`);
  if (p.mobile) await closeDrawer(p);
  return items;
}
function selectorFor(x) { return x.id ? `#${x.id}` : `[${x.attr}=${JSON.stringify(x.value)}]`; }
async function route(p, role, item) {
  await navigate(p, `&role=${encodeURIComponent(role)}&route=${encodeURIComponent(item.label)}`);
  await setRole(role);
  if (p.mobile) await openDrawer(p);
  const selector = selectorFor(item), before = await shell();
  const already = await evalJs(`document.querySelector(${JSON.stringify(selector)})?.classList.contains('active')||false`);
  await activate(selector, p, 520);
  const after = await shell();
  const changed = before.page !== after.page || before.title !== after.title || before.modal !== after.modal || before.chat !== after.chat;
  const closed = !p.mobile || (!after.drawer && !after.scrim);
  let reopened = true;
  if (p.mobile) { try { await openDrawer(p); await closeDrawer(p); } catch { reopened = false; } }
  return { role, label: item.label, selector, before, after, changed, already, closed, reopened, ok: closed && reopened && (changed || already || after.modal || after.chat) };
}
async function fingerprint() {
  return evalJs(`(()=>JSON.stringify({page:document.querySelector('.page.active')?.id||'',title:document.querySelector('.page.active h1,.page.active h2')?.textContent||'',modal:document.querySelector('#modal')?.classList.contains('open')?(document.querySelector('#modalTitle')?.textContent||'')+(document.querySelector('#modalBody')?.textContent||'').slice(0,250):'',toast:document.querySelector('#toast.show')?.textContent||document.querySelector('#hunterNativeDictationToast')?.textContent||'',active:[...document.querySelectorAll('.active,.open,.show')].slice(0,100).map(e=>e.id||e.getAttribute('data-view')||String(e.className)).join('|'),values:[...document.querySelectorAll('input:not([type=file]),textarea,select')].filter(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'}).map(e=>[e.id||e.name||'',e.type==='checkbox'?e.checked:e.value])}))()`);
}
async function fillForms() {
  await evalJs(`(()=>{const vis=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&s.display!=='none'};for(const e of document.querySelectorAll('.page.active input:not([type=file]):not([type=checkbox]):not([type=radio]),.page.active textarea,#modal.open input:not([type=file]):not([type=checkbox]):not([type=radio]),#modal.open textarea')){if(!vis(e)||e.disabled||e.readOnly||e.value)continue;e.value=e.type==='email'?'proof@example.com':e.type==='number'?'1':'Sergeant full standard proof';e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:e.value}));e.dispatchEvent(new Event('change',{bubbles:true}))}})()`);
}
async function controls() {
  return evalJs(`(()=>{const root=document.querySelector('.page.active');if(!root)return[];const vis=e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>=24&&r.height>=24&&s.display!=='none'&&s.visibility!=='hidden'};const keys=['data-case','data-open-client','data-conversation','data-case-action','data-inbox-action','data-file-replace','data-file-remove','data-person-op','data-manage-person','data-person-activity','data-connection-manage','data-connection-test','data-knowledge','data-accountability','data-client-role','data-tracking-stage','data-family-workflow','data-family-trail','data-family-step','data-generic','data-stage','data-task','data-role-route','data-copy','data-good','data-bad','data-share','data-sources','data-more','data-regenerate','data-report','data-settings-tab','data-pref-toggle','data-pref-select','data-final-settings','data-final-toggle','data-final-action','data-final-pref','data-wa-view','data-wa-mode','data-wa-attach','data-wa-send','data-wa-promo','data-polish-mode','data-polish-attach','data-polish-send','data-polish-promo','data-promo-preview','data-promo-publish','data-notice','data-attention','data-promo-placement'];return [...root.querySelectorAll('button,a[href],[role=button],select,input[type=checkbox],input[type=radio]')].filter(vis).filter(e=>!e.disabled&&e.getAttribute('aria-disabled')!=='true').filter(e=>!e.closest('#nav,#hunterUnifiedChatNav,.account-zone')).map((e,i)=>{const pair=keys.map(k=>[k,e.getAttribute(k)]).find(x=>x[1]!==null);return{id:e.id||'',attr:pair?.[0]||'',value:pair?.[1]||'',label:(e.getAttribute('aria-label')||e.title||e.textContent||e.value||'').replace(/\s+/g,' ').trim(),tag:e.tagName,type:e.type||'',active:e.classList.contains('active')||e.getAttribute('aria-pressed')==='true',i}}).filter(x=>x.id||x.attr)})()`);
}
const sideEffect = x => /attach|share|copy|sound|microphone|dictate|download/i.test(x.label) || ["#hcs2Attach","#hcs2Voice","[data-share]","[data-preview-sound]","[data-wa-attach]"].includes(selectorFor(x));
async function exerciseControl(p, nav, control) {
  await route(p, "owner", nav);
  await fillForms();
  const selector = selectorFor(control), usable = await point(selector);
  if (!usable?.visible) return { skipped: true, label: control.label };
  const before = await fingerprint();
  if (control.tag === "SELECT") {
    await evalJs(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e||e.options.length<2)return;e.selectedIndex=(e.selectedIndex+1)%e.options.length;e.dispatchEvent(new Event('input',{bubbles:true}));e.dispatchEvent(new Event('change',{bubbles:true}))})()`);
    await sleep(350);
  } else await activate(selector, p, 480);
  const after = await fingerprint(), state = await shell();
  const changed = before !== after, ok = state.overflow <= 1 && (changed || sideEffect(control) || control.active);
  return { page: nav.label, label: control.label, selector, changed, sideEffect: sideEffect(control), active: control.active, overflow: state.overflow, ok };
}
async function keyboard(p) {
  if (p.mobile) return { skipped: true };
  await navigate(p, "&keyboard=1");
  const seen = [];
  for (let i=0;i<24;i++) { await cdp("Input.dispatchKeyEvent", { type:"keyDown", key:"Tab", code:"Tab", windowsVirtualKeyCode:9, nativeVirtualKeyCode:9 }); await cdp("Input.dispatchKeyEvent", { type:"keyUp", key:"Tab", code:"Tab", windowsVirtualKeyCode:9, nativeVirtualKeyCode:9 }); await sleep(25); seen.push(await evalJs("document.activeElement?.id||document.activeElement?.getAttribute('data-view')||document.activeElement?.getAttribute('aria-label')||document.activeElement?.tagName||''")); }
  const unique=[...new Set(seen.filter(Boolean))]; return { seen, unique, ok: unique.length>=8 };
}

const proof = { targetUrl, standard:"finish-then-prove/full-mobile-desktop-interface-v2", startedAt:new Date().toISOString(), endpoints:{}, profiles:{}, runtimeErrors, consoleErrors, networkFailures, unsafeRequests };
try {
  const origin = new URL(targetUrl).origin;
  for (const path of ["/health","/portal","/api/system/version"]) { const r=await fetch(origin+path); proof.endpoints[path]={status:r.status,ok:r.ok}; if(!r.ok)throw new Error(`${path} failed ${r.status}`); }
  const tabs=await waitJson(`http://127.0.0.1:${debugPort}/json/list`), target=tabs.find(t=>t.type==="page")||tabs[0];
  ws=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{ws.addEventListener("open",resolve,{once:true});ws.addEventListener("error",reject,{once:true})});
  ws.addEventListener("message",e=>{const m=JSON.parse(String(e.data));if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result||{});return}if(m.method==="Runtime.exceptionThrown")runtimeErrors.push(m.params);if(m.method==="Runtime.consoleAPICalled"&&["error","assert"].includes(m.params?.type))consoleErrors.push(m.params);if(m.method==="Network.loadingFailed"&&!m.params?.canceled)networkFailures.push(m.params);if(m.method==="Network.requestWillBeSent"&&!['GET','HEAD','OPTIONS'].includes(m.params?.request?.method))unsafeRequests.push({method:m.params.request.method,url:m.params.request.url})});
  await cdp("Runtime.enable");await cdp("Page.enable");await cdp("Network.enable");
  for (const p of profiles) {
    const result={roles:[],navigation:[],controls:[],keyboard:null,sergeant:null};
    await navigate(p); result.roles=await roles();
    for(const role of result.roles){await navigate(p,`&inventory=${role}`);await setRole(role);const items=await navItems(p);if(!items.length&&role!=='regular')throw new Error(`${p.name}/${role}: no menu destinations`);for(const item of items){const r=await route(p,role,item);result.navigation.push(r);if(!r.ok)throw new Error(`${p.name}/${role}/${item.label}: broken navigation ${JSON.stringify(r)}`)}}
    await navigate(p,"&sergeant=1");if(await evalJs("!!globalThis.__HUNTER_SERGEANT_UI__")){result.sergeant=await evalJs("globalThis.__HUNTER_SERGEANT_UI__.critical().then(()=>globalThis.__HUNTER_SERGEANT_UI__.report())");if(!result.sergeant?.passed)throw new Error(`${p.name}: Sergeant critical failed ${JSON.stringify(result.sergeant)}`)}
    if(p.name!=="wide-1920x1080"){
      await navigate(p,"&owner-controls=1");await setRole("owner");const ownerNav=await navItems(p);for(const nav of ownerNav){await route(p,"owner",nav);const list=await controls();for(const control of list){const r=await exerciseControl(p,nav,control);result.controls.push(r);if(r.ok===false)throw new Error(`${p.name}/${nav.label}/${control.label}: dead control ${JSON.stringify(r)}`)}}
    }
    result.keyboard=await keyboard(p);if(result.keyboard?.ok===false)throw new Error(`${p.name}: keyboard traversal failed`);
    await navigate(p,"&final=1");const final=await shell();if(final.overflow>1)throw new Error(`${p.name}: horizontal overflow ${final.overflow}`);await screenshot(`${p.name}-final.png`);result.final=final;proof.profiles[p.name]=result;await writeFile(join(outDir,"proof-progress.json"),JSON.stringify(proof,null,2));
  }
  if(runtimeErrors.length)throw new Error(`Runtime exceptions ${JSON.stringify(runtimeErrors.slice(0,5))}`);if(consoleErrors.length)throw new Error(`Console errors ${JSON.stringify(consoleErrors.slice(0,5))}`);if(networkFailures.length)throw new Error(`Network failures ${JSON.stringify(networkFailures.slice(0,5))}`);if(unsafeRequests.length)throw new Error(`Review attempted writes ${JSON.stringify(unsafeRequests.slice(0,10))}`);
  proof.passed=true;proof.completedAt=new Date().toISOString();await writeFile(join(outDir,"proof.json"),JSON.stringify(proof,null,2));console.log("SRG FULL STANDARD V2 PASS: real-touch mobile menus, every role route, owner controls, desktop/wide layouts, keyboard, runtime and no-write boundary passed.");
} catch(error) {
  proof.passed=false;proof.error=String(error?.stack||error);proof.completedAt=new Date().toISOString();await writeFile(join(outDir,"proof.json"),JSON.stringify(proof,null,2));try{await screenshot("99-full-standard-failure.png")}catch{}throw error;
} finally {try{ws?.close()}catch{}chrome.kill("SIGTERM");await sleep(300);if(!chrome.killed)chrome.kill("SIGKILL")}
