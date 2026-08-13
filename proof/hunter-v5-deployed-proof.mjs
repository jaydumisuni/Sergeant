import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const TARGET = process.env.HUNTER_V5_URL || 'https://a22916c4-hunter-ui-review.thetechguy712.workers.dev/portal';
const OUT = process.env.HUNTER_V5_OUT || 'proof-output/hunter-v5-deployed';
const EXPECTED_REVIEW = 'approved-workspace-v5';
const viewports = [
  { name: 'phone', width: 390, height: 844, mobile: true },
  { name: 'tablet', width: 820, height: 1180, mobile: true },
  { name: 'desktop', width: 1440, height: 900, mobile: false },
  { name: 'wide', width: 1920, height: 1080, mobile: false },
];

await fs.mkdir(OUT, { recursive: true });
const report = { target: TARGET, expectedReview: EXPECTED_REVIEW, startedAt: new Date().toISOString(), viewports: [], findings: [] };
const addFinding = (viewport, phase, message, detail = null) => report.findings.push({ viewport, phase, message, detail });

function textOf(v) { return String(v || '').replace(/\s+/g, ' ').trim(); }

async function screenshot(page, viewport, name) {
  const file = path.join(OUT, `${viewport}-${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  return file;
}

async function openDrawerIfNeeded(page, mobile) {
  if (!mobile) return;
  const sidebar = page.locator('#sidebar');
  if (await sidebar.count()) {
    const isOpen = await sidebar.evaluate(el => el.classList.contains('open')).catch(() => false);
    if (isOpen) return;
  }
  const menu = page.locator('#menuBtn');
  if (await menu.count()) {
    await menu.first().click({ timeout: 5000 });
    await page.waitForTimeout(120);
  }
}

async function clickNav(page, mobile, pattern) {
  await openDrawerIfNeeded(page, mobile);
  const candidates = page.locator('#sidebar button, #sidebar a, nav button, nav a').filter({ hasText: pattern });
  const count = await candidates.count();
  if (!count) throw new Error(`No navigation control matched ${pattern}`);
  for (let i = 0; i < count; i++) {
    const item = candidates.nth(i);
    if (await item.isVisible().catch(() => false)) {
      await item.scrollIntoViewIfNeeded();
      await item.click({ timeout: 5000 });
      await page.waitForTimeout(180);
      return;
    }
  }
  throw new Error(`Navigation control matched ${pattern} but none was visible`);
}

async function assertNoOverflow(page, viewport, phase) {
  const metrics = await page.evaluate(() => ({
    innerWidth: window.innerWidth,
    scrollWidth: document.documentElement.scrollWidth,
    bodyScrollWidth: document.body?.scrollWidth || 0,
  }));
  if (metrics.scrollWidth > metrics.innerWidth + 1 || metrics.bodyScrollWidth > metrics.innerWidth + 1) {
    addFinding(viewport, phase, 'horizontal overflow', metrics);
  }
  return metrics;
}

const browser = await chromium.launch({ headless: true });
try {
  for (const vp of viewports) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
      isMobile: vp.mobile,
      hasTouch: vp.mobile,
    });
    const page = await context.newPage();
    const pageErrors = [];
    const consoleErrors = [];
    const mutatingRequests = [];
    page.on('pageerror', error => pageErrors.push(String(error)));
    page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    page.on('request', req => { if (['POST','PUT','PATCH','DELETE'].includes(req.method())) mutatingRequests.push({ method: req.method(), url: req.url() }); });

    const vr = { name: vp.name, width: vp.width, height: vp.height, phases: {}, screenshots: [] };
    report.viewports.push(vr);

    let response;
    try {
      response = await page.goto(TARGET, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForTimeout(900);
    } catch (error) {
      addFinding(vp.name, 'load', 'failed to load exact deployed preview', String(error));
      await context.close();
      continue;
    }

    const headers = response ? await response.allHeaders() : {};
    vr.status = response?.status() ?? null;
    vr.headers = {
      review: headers['x-hunter-review'] || null,
      htmlSha256: headers['x-hunter-html-sha256'] || null,
      production: headers['x-hunter-production'] || null,
    };
    if (vr.status !== 200) addFinding(vp.name, 'load', `HTTP ${vr.status}`);
    if (vr.headers.review !== EXPECTED_REVIEW) addFinding(vp.name, 'load', 'wrong review marker', vr.headers);
    const version = await page.evaluate(() => globalThis.__HUNTER_V5_OWNER_CORRECTIONS__?.version || null);
    vr.v5Version = version;
    if (version !== 'HUNTER_EMPLOYEE_OS_APPROVED_WORKSPACE_V5_OWNER_CORRECTIONS') addFinding(vp.name, 'load', 'V5 runtime marker missing', version);

    // 1. Department/role landing must begin with Talk to Hunter rather than Today.
    const initial = await page.evaluate(() => {
      const activeNav = [...document.querySelectorAll('#sidebar button.active,#sidebar a.active,nav button.active,nav a.active,[aria-current="page"]')]
        .map(el => (el.textContent || el.getAttribute('aria-label') || '').replace(/\s+/g,' ').trim())
        .filter(Boolean);
      const activePage = document.querySelector('.page.active,[data-page].active');
      return { activeNav, activePage: activePage?.getAttribute('data-page') || null, bodyText: (document.body.innerText || '').slice(0, 5000) };
    });
    vr.phases.landing = initial;
    const hunterLanding = initial.activeNav.some(t => /talk to hunter/i.test(t)) || initial.activePage === 'hunter-chat' || /what do you need done|message hunter/i.test(initial.bodyText);
    const todayLanding = initial.activeNav.some(t => /^today$/i.test(t)) || initial.activePage === 'today';
    if (!hunterLanding || todayLanding) addFinding(vp.name, 'landing', 'role/department did not land on Talk to Hunter', initial);
    vr.screenshots.push(await screenshot(page, vp.name, '01-hunter-landing'));
    vr.phases.landingMetrics = await assertNoOverflow(page, vp.name, 'landing');

    // 2. Inbox must be WhatsApp-like and switch between Conversation and a compact Respond surface.
    try {
      await clickNav(page, vp.mobile, /Inbox|Conversation/i);
      await page.locator('[data-v5-surface="inbox"]').waitFor({ state: 'visible', timeout: 6000 });
      const inboxText = textOf(await page.locator('[data-v5-surface="inbox"]').innerText());
      if (!/WhatsApp/.test(inboxText) || !/Maya \+ Hunter/.test(inboxText) || !/Conversation/.test(inboxText) || !/Respond/.test(inboxText)) {
        addFinding(vp.name, 'inbox-conversation', 'WhatsApp conversation contract incomplete', inboxText.slice(0, 1500));
      }
      vr.screenshots.push(await screenshot(page, vp.name, '02-whatsapp-conversation'));
      await assertNoOverflow(page, vp.name, 'inbox-conversation');

      await page.locator('[data-v5-inbox-view="respond"]').click();
      await page.locator('.v5-wa-respond').waitFor({ state: 'visible', timeout: 4000 });
      const respondText = textOf(await page.locator('.v5-wa-respond').innerText());
      const conversationCount = await page.locator('.v5-wa-conversation').count();
      if (!/Replying on WhatsApp/.test(respondText) || !/Maya \+ Hunter/.test(respondText) || !/Employee reply/.test(respondText) || !/Propose alternative/.test(respondText) || !/Confirm & send/.test(respondText)) {
        addFinding(vp.name, 'inbox-respond', 'Respond contract incomplete', respondText.slice(0, 1500));
      }
      if (conversationCount !== 0) addFinding(vp.name, 'inbox-respond', 'Respond still stacks full conversation above composer', { conversationCount });
      vr.screenshots.push(await screenshot(page, vp.name, '03-whatsapp-respond'));
      await assertNoOverflow(page, vp.name, 'inbox-respond');
    } catch (error) {
      addFinding(vp.name, 'inbox', 'Inbox interaction failed', String(error));
    }

    // 3. Tracking must expose the recovered Admin Tracking Operations model and preserve payment truth.
    try {
      await clickNav(page, vp.mobile, /Tracking/i);
      await page.locator('[data-v5-surface="tracking"]').waitFor({ state: 'visible', timeout: 6000 });
      const trackingText = textOf(await page.locator('[data-v5-surface="tracking"]').innerText());
      const requiredTracking = ['Tracking Operations','D1 jobs','Selected job','Stage','Location','Shipping cost','Update note','Update D1','Link phone','Carrier tracking','Job truth','PAYMENT_SUBMITTED','WhatsApp/screenshots/claims do not mark PAID'];
      const missing = requiredTracking.filter(marker => !trackingText.includes(marker));
      if (missing.length) addFinding(vp.name, 'tracking', 'Tracking Operations contract incomplete', { missing });
      vr.screenshots.push(await screenshot(page, vp.name, '04-tracking-operations'));
      await assertNoOverflow(page, vp.name, 'tracking');
    } catch (error) {
      addFinding(vp.name, 'tracking', 'Tracking interaction failed', String(error));
    }

    // 4. Browser icon must be present and open the truthful review-only Browser panel.
    try {
      const browserButton = page.locator('#v5BrowserBtn');
      await browserButton.waitFor({ state: 'visible', timeout: 5000 });
      await browserButton.click();
      await page.locator('#v5BrowserModal').waitFor({ state: 'visible', timeout: 4000 });
      const browserText = textOf(await page.locator('#v5BrowserModal').innerText());
      if (!/Hunter Browser/.test(browserText) || !/Browser session not connected in this review/.test(browserText) || !/no connected browser session/i.test(browserText)) {
        addFinding(vp.name, 'browser', 'Browser panel is not the truthful approved review state', browserText.slice(0, 1200));
      }
      vr.screenshots.push(await screenshot(page, vp.name, '05-browser-panel'));
      await assertNoOverflow(page, vp.name, 'browser');
    } catch (error) {
      addFinding(vp.name, 'browser', 'Browser control failed', String(error));
    }

    vr.pageErrors = pageErrors;
    vr.consoleErrors = consoleErrors;
    vr.mutatingRequests = mutatingRequests;
    if (pageErrors.length) addFinding(vp.name, 'runtime', 'page errors observed', pageErrors);
    if (consoleErrors.length) addFinding(vp.name, 'runtime', 'console errors observed', consoleErrors);
    if (mutatingRequests.length) addFinding(vp.name, 'write-boundary', 'unexpected mutating network request from review proof', mutatingRequests);

    await context.close();
  }
} finally {
  await browser.close();
}

report.finishedAt = new Date().toISOString();
report.passed = report.findings.length === 0 && report.viewports.length === viewports.length;
await fs.writeFile(path.join(OUT, 'report.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ passed: report.passed, findings: report.findings.length, target: TARGET }, null, 2));
if (!report.passed) process.exitCode = 1;
