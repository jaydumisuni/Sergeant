const { test, expect } = require('@playwright/test');
const path = require('path');
const { pathToFileURL } = require('url');

const preview = process.env.COMMAND_CENTER_PREVIEW || path.join(process.cwd(), 'build', 'command-center-preview.html');
const previewUrl = pathToFileURL(preview).href;
const pages = [
  ['Dashboard', 'dashboard'],
  ['Mission Planner', 'orders'],
  ['Evidence', 'evidence'],
  ['Evidence Locker', 'reports'],
  ['Officers / Armoury', 'squad'],
  ['Settings', 'settings'],
  ['Doctrine', 'doctrine'],
  ['Roadmap', 'roadmap'],
  ['Guide', 'guide'],
];

async function assertCommandCenter(page, screenshotName) {
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  await page.goto(previewUrl);
  await expect(page.locator('h1')).toContainText('SGT');
  await expect(page.locator('#dashboardOfficers .officer')).toHaveCount(5);

  for (const [label, id] of pages) {
    await page.getByRole('button', { name: label, exact: true }).first().click();
    await expect(page.locator(`#${id}`)).toBeVisible();
  }

  await page.getByRole('button', { name: 'Mission Planner', exact: true }).first().click();
  await expect(page.locator('#providerSelect')).toBeVisible();
  await expect(page.locator('#deployBtn')).toBeVisible();

  await page.getByRole('button', { name: 'Dashboard', exact: true }).first().click();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(2);
  expect(pageErrors).toEqual([]);
  await page.screenshot({ path: path.join('artifacts', screenshotName), fullPage: true });
}

test('full Command Center renders, navigates, and avoids floating-control overlap', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  await assertCommandCenter(page, 'command-center-1600.png');

  const overlaps = await page.evaluate(() => {
    const quick = document.querySelector('.quick-actions')?.getBoundingClientRect();
    if (!quick) return [];
    return [...document.querySelectorAll('.page.active .panel, .page.active .commander article')]
      .map((element) => ({ element, box: element.getBoundingClientRect() }))
      .filter(({ box }) => box.width > 0 && box.height > 0)
      .filter(({ box }) => quick.left < box.right && quick.right > box.left && quick.top < box.bottom && quick.bottom > box.top)
      .map(({ element }) => element.textContent.trim().slice(0, 60));
  });
  expect(overlaps).toEqual([]);
});

test('compact IDE width remains usable without confidence-label collision', async ({ page }) => {
  await page.setViewportSize({ width: 420, height: 920 });
  await assertCommandCenter(page, 'command-center-420.png');

  const collisions = await page.evaluate(() => [...document.querySelectorAll('.confidence-line')].filter((line) => {
    const label = line.querySelector('span:first-child')?.getBoundingClientRect();
    const bar = line.querySelector('.bar')?.getBoundingClientRect();
    return label && bar && label.right > bar.left + 1;
  }).map((line) => line.textContent.trim()));
  expect(collisions).toEqual([]);
});

test('mission briefing is emitted as an audit payload', async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 900 });
  await page.goto(previewUrl);
  await page.getByRole('button', { name: 'Mission Planner', exact: true }).first().click();
  await page.locator('#missionBriefing').fill('Verify the release candidate with runtime proof.');
  await page.locator('#priority').selectOption('Release Critical');
  await page.locator('#providerSelect').selectOption('GPT');
  await page.locator('#deployBtn').click();

  const payload = await page.evaluate(() => JSON.parse(window.__sergeantLastPayload));
  expect(payload.type).toBe('run');
  expect(payload.action).toBe('reviewWorkspace');
  expect(payload.mission).toMatchObject({
    type: 'Repository Review',
    briefing: 'Verify the release candidate with runtime proof.',
    priority: 'Release Critical',
    provider: 'GPT',
  });
  expect(payload.mission.loadout.length).toBeGreaterThan(0);
});

test('runtime state is escaped before evidence and history rendering', async ({ page }) => {
  await page.setViewportSize({ width: 1200, height: 900 });
  await page.goto(previewUrl);
  const hostile = '<img data-evil src=x onerror="window.__sergeantInjected=true">';
  await page.evaluate((value) => {
    window.__sergeantInjected = false;
    window.postMessage({
      type: 'sergeantState',
      state: {
        status: 'Complete',
        workspace: value,
        workspaces: [value],
        branch: value,
        platform: 'VS Code',
        changedFilesCount: 1,
        currentMission: { type: value, provider: value },
        history: [{ id: value, mission: value, result: 'PASS', date: value, duration: value }],
        last: {
          title: value,
          missionContext: { type: value, provider: value },
          summary: { verdict: 'PASS' },
          findings: [{ message: value }],
          finishedAt: value,
          justFinished: false,
        },
      },
    }, '*');
  }, hostile);

  await expect(page.locator('#currentWorkspace')).toHaveText(hostile);
  await page.getByRole('button', { name: 'Evidence', exact: true }).first().click();
  await expect(page.locator('#evidenceCards')).toContainText(hostile);
  expect(await page.evaluate(() => window.__sergeantInjected)).toBe(false);
  await expect(page.locator('img[data-evil]')).toHaveCount(0);
});
