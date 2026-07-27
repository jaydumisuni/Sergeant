const { test, expect } = require('@playwright/test');
const { pathToFileURL } = require('url');
const path = require('path');

const docsPreview = process.env.MODEL_FREE_DOCS_PREVIEW;
const commandCenterPreview = process.env.COMMAND_CENTER_PREVIEW;
const artifacts = path.resolve(process.env.VISUAL_ARTIFACTS || 'artifacts/model-free-product');

async function openLocal(page, filePath) {
  if (!filePath) throw new Error('Visual preview path is missing.');
  await page.goto(pathToFileURL(path.resolve(filePath)).href);
  await page.waitForLoadState('domcontentloaded');
}

async function expectNoDocumentOverflow(page) {
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    document: document.documentElement.scrollWidth,
  }));
  expect(dimensions.document).toBeLessThanOrEqual(dimensions.viewport + 1);
}

for (const view of [
  { name: 'desktop', width: 1600, height: 1200 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  test(`model-free documentation is readable on ${view.name}`, async ({ page }) => {
    await page.setViewportSize({ width: view.width, height: view.height });
    await openLocal(page, docsPreview);
    await expect(page.locator('body')).toContainText('Sergeant is a model-free engineering review system');
    await expect(page.locator('body')).toContainText('Optional extra reasoning');
    await expect(page.locator('body')).toContainText('A multi-model council is only one optional configuration');
    const hero = page.locator('img[alt="Sergeant - open-source engineering reviewer"]');
    await expect(hero).toBeVisible();
    const imageState = await hero.evaluate((image) => ({
      complete: image.complete,
      naturalWidth: image.naturalWidth,
      renderedWidth: image.getBoundingClientRect().width,
      containerWidth: image.parentElement?.getBoundingClientRect().width || 0,
    }));
    expect(imageState.complete).toBe(true);
    expect(imageState.naturalWidth).toBeGreaterThan(0);
    expect(imageState.renderedWidth).toBeGreaterThan(0);
    expect(imageState.renderedWidth).toBeLessThanOrEqual(imageState.containerWidth + 1);
    await expectNoDocumentOverflow(page);
    await page.screenshot({
      path: path.join(artifacts, `model-free-docs-${view.name}.png`),
      fullPage: true,
    });
  });

  test(`Command Center shows model-free default on ${view.name}`, async ({ page }) => {
    await page.setViewportSize({ width: view.width, height: view.height });
    await openLocal(page, commandCenterPreview);
    await page.locator('[data-page="orders"]').first().click();
    await expect(page.locator('h4', { hasText: 'Cpl — Model-Free Core / Optional Model Support' })).toBeVisible();
    await expect(page.locator('#llmPolicySelect')).toHaveValue('disabled');
    await expect(page.locator('body')).toContainText('Model-free only — no model calls');
    await expect(page.locator('body')).toContainText('optional extra-reasoning support only');
    await expect(page.locator('.quick-actions')).toBeHidden();
    const controls = await page.locator('#orders article.panel').nth(1).locator('input, select').evaluateAll((elements) =>
      elements.map((element) => {
        const box = element.getBoundingClientRect();
        return { id: element.id, left: box.left, right: box.right, top: box.top, bottom: box.bottom };
      }),
    );
    for (let index = 0; index < controls.length; index += 1) {
      for (let other = index + 1; other < controls.length; other += 1) {
        const first = controls[index];
        const second = controls[other];
        const overlaps = first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top;
        expect(overlaps, `${first.id} overlaps ${second.id}`).toBeFalsy();
      }
    }
    if (view.name === 'desktop') {
      const reasoningWidth = await page.locator('#llmCouncilSelect').evaluate((element) => element.getBoundingClientRect().width);
      expect(reasoningWidth).toBeGreaterThan(230);
    }
    await expect(page.locator('body')).toContainText('Optional Model Limits');
    await expectNoDocumentOverflow(page);
    await page.screenshot({
      path: path.join(artifacts, `model-free-command-center-${view.name}.png`),
      fullPage: true,
    });
  });
}
