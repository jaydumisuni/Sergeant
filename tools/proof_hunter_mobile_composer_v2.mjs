import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join } from "node:path";

const targetUrl=process.env.HUNTER_REVIEW_URL;
if(!targetUrl)throw new Error("HUNTER_REVIEW_URL is required");
const outDir=process.env.PROOF_DIR||"artifacts/hunter-mobile-composer";
await mkdir(outDir,{recursive:true});
const chromePath=[process.env.CHROME_PATH,"/usr/bin/google-chrome","/usr/bin/google-chrome-stable","/usr/bin/chromium"].filter(Boolean).find(existsSync);
if(!chromePath)throw new Error("Chrome unavailable");
const port=9245;
const chrome=spawn(chromePath,["--headless=new","--no-sandbox","--disable-gpu","--hide-scrollbars",`--remote-debugging-port=${port}`,`--user-data-dir=${join(process.env.RUNNER_TEMP||"/tmp",`srg-composer-v2-${Date.now()}`)}`,"--window-size=390,844","about:blank"],{stdio:["ignore","pipe","pipe"]});
let log="";chrome.stdout.on("data",d=>log+=String(d));chrome.stderr.on("data",d=>log+=String(d));
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function waitJson(url){for(let i=0;i<120;i++){try{const r=await fetch(url);if(r.ok)return r.json()}catch{}await sleep(250)}throw new Error(`timeout ${url}\n${log.slice(-3000)}`)}
let ws,id=0;const pending=new Map();
function cdp(method,params={}){const n=++id;return new Promise((resolve,reject)=>{pending.set(n,{resolve,reject});ws.send(JSON.stringify({id:n,method,params}))})}
async function ev(expression){const r=await cdp("Runtime.evaluate",{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw new Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text||"eval failed");return r.result?.value}
async function waitFor(expression,label,attempts=120){for(let i=0;i<attempts;i++){try{if(await ev(expression))return}catch{}await sleep(100)}throw new Error(`timeout ${label}`)}
async function point(selector){return ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return null;const r=e.getBoundingClientRect(),x=r.left+r.width/2,y=r.top+r.height/2,h=document.elementFromPoint(x,y);return{x,y,width:r.width,height:r.height,visible:getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'&&r.width>0&&r.height>0,hit:h===e||!!h?.closest?.(${JSON.stringify(selector)}),hitTag:h?.tagName||'',hitId:h?.id||'',hitClass:String(h?.className||'')}})()`)}
async function touch(selector,settle=150){const p=await point(selector);if(!p?.visible||!p.hit||p.width<28||p.height<28)throw new Error(`unusable ${selector}: ${JSON.stringify(p)}`);await cdp("Input.dispatchTouchEvent",{type:"touchStart",touchPoints:[{x:p.x,y:p.y,radiusX:6,radiusY:6,force:1,id:1}]});await sleep(45);await cdp("Input.dispatchTouchEvent",{type:"touchEnd",touchPoints:[]});await sleep(settle);return p}
async function shot(name){const r=await cdp("Page.captureScreenshot",{format:"png",fromSurface:true,captureBeyondViewport:false});await writeFile(join(outDir,name),Buffer.from(r.data,"base64"))}
async function state(stage){return ev(`(()=>{const i=document.querySelector('#hcs2Input'),v=document.querySelector('#hcs2Voice'),a=globalThis.__HUNTER_CHAT_COMPOSER_RELIABILITY_AUDIT__;const r=i?.getBoundingClientRect();return{stage:${JSON.stringify(stage)},activeId:document.activeElement?.id||'',input:i?.value||'',inputRect:r?{left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height}:null,inputDisabled:!!i?.disabled,inputReadOnly:!!i?.readOnly,userMessages:document.querySelectorAll('.hcs2-row.user').length,hunterMessages:document.querySelectorAll('.hcs2-row.hunter').length,voiceLayer:!!document.querySelector('#hunterVoiceLayer'),voiceLabel:v?.getAttribute('aria-label')||'',toast:document.querySelector('#hunterNativeDictationToast')?.textContent||'',audit:a||null}})()`)}

const proof={targetUrl,viewport:{width:390,height:844},inputMode:"trusted touch plus browser keyboard insertion",stages:[],startedAt:new Date().toISOString()};
try{
 const tabs=await waitJson(`http://127.0.0.1:${port}/json/list`),target=tabs.find(t=>t.type==='page')||tabs[0];
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
 ws.addEventListener('message',e=>{const m=JSON.parse(String(e.data));if(!m.id||!pending.has(m.id))return;const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(new Error(JSON.stringify(m.error))):p.resolve(m.result||{})});
 await cdp("Runtime.enable");await cdp("Page.enable");await cdp("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:3,mobile:true,screenWidth:390,screenHeight:844});await cdp("Emulation.setTouchEmulationEnabled",{enabled:true,maxTouchPoints:5});await cdp("Emulation.setUserAgentOverride",{userAgent:"Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",platform:"iPhone"});
 await cdp("Page.navigate",{url:targetUrl});await waitFor("document.readyState==='complete'&&!!globalThis.__HUNTER_MOBILE_SIDEBAR__","runtime");
 await touch('#mobileMenu',100);await waitFor("document.querySelector('#sidebar')?.classList.contains('open')","drawer");
 const chat=await ev(`(()=>{const b=[...document.querySelectorAll('#sidebar button,#sidebar a')].find(x=>/Talk to Hunter/i.test((x.textContent||'').replace(/\\s+/g,' ').trim()));if(!b)return null;b.dataset.srgComposerV2='true';return '#sidebar [data-srg-composer-v2="true"]'})()`);if(!chat)throw new Error('Talk to Hunter missing');
 await touch(chat,250);await waitFor("document.querySelector('#page-hunter-chat')?.classList.contains('active')&&!!document.querySelector('#hcs2Input')&&!!globalThis.__HUNTER_CHAT_COMPOSER_RELIABILITY__","chat composer");await sleep(350);
 const ready=await state('ready');proof.stages.push(ready);if(ready.inputDisabled||ready.inputReadOnly||ready.inputRect?.width<80)throw new Error(`input unavailable ${JSON.stringify(ready)}`);await shot('01-ready.png');
 await touch('#hcs2Input',500);await waitFor("document.activeElement?.id==='hcs2Input'","redraw-safe focus",30);const focused=await state('focused');proof.stages.push(focused);if(!focused.audit?.passed)throw new Error(`post-touch audit failed ${JSON.stringify(focused.audit)}`);await shot('02-focused.png');
 await cdp("Input.insertText",{text:"hello from the phone keyboard"});await waitFor("document.querySelector('#hcs2Input')?.value==='hello from the phone keyboard'","keyboard text");const typed=await state('typed');proof.stages.push(typed);if(typed.activeId!=='hcs2Input')throw new Error(`focus lost ${JSON.stringify(typed)}`);await shot('03-typed.png');
 const users=typed.userMessages,hunters=typed.hunterMessages;await touch('#hcs2Send',260);await waitFor(`document.querySelectorAll('.hcs2-row.user').length===${users+1}`,"typed send");await waitFor(`document.querySelectorAll('.hcs2-row.hunter').length>${hunters}`,"Hunter reply");const sent=await state('sent');proof.stages.push(sent);await shot('04-sent.png');
 await touch('#hcs2Voice',180);await waitFor("document.activeElement?.id==='hcs2Input'&&!!document.querySelector('#hunterNativeDictationToast')","native dictation");const voice=await state('native-dictation');proof.stages.push(voice);if(voice.voiceLayer)throw new Error('dead voice popup opened');if(!/Dictate message/i.test(voice.voiceLabel))throw new Error(`wrong voice label ${voice.voiceLabel}`);if(!/microphone on your keyboard/i.test(voice.toast))throw new Error(`dictation guidance missing ${voice.toast}`);if(!voice.audit?.lastVoiceFallback?.focused)throw new Error(`dictation focus missing ${JSON.stringify(voice.audit)}`);await shot('05-native-dictation.png');
 proof.passed=true;proof.completedAt=new Date().toISOString();await writeFile(join(outDir,'proof.json'),JSON.stringify(proof,null,2));console.log('SRG COMPOSER PASS: real mobile typing, send, Hunter reply and iPhone native dictation all work.');
}catch(error){proof.passed=false;proof.error=String(error?.stack||error);proof.completedAt=new Date().toISOString();await writeFile(join(outDir,'proof.json'),JSON.stringify(proof,null,2));try{await shot('99-failure.png')}catch{}throw error}finally{try{ws?.close()}catch{}chrome.kill('SIGTERM');await sleep(250);if(!chrome.killed)chrome.kill('SIGKILL')}
