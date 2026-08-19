// Рендерит слайды карусели: статичные — скриншотом, анимированную обложку —
// записью видео (Playwright recordVideo) с CSS-анимацией на странице.
// Запуск: NODE_PATH=<где лежит playwright> node screenshot.cjs manifest.json
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

async function main() {
  const manifestPath = process.argv[2];
  if (!manifestPath) {
    console.error('usage: node screenshot.cjs manifest.json');
    process.exit(1);
  }

  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  const browser = await chromium.launch();

  try {
    for (const slide of manifest.slides) {
      const fileUrl = 'file://' + slide.html;

      if (slide.animated) {
        fs.mkdirSync(slide.videoDir, { recursive: true });
        const context = await browser.newContext({
          viewport: { width: slide.width, height: slide.height },
          recordVideo: { dir: slide.videoDir, size: { width: slide.width, height: slide.height } },
        });
        const page = await context.newPage();
        await page.goto(fileUrl);
        if (slide.stillOut) {
          fs.mkdirSync(path.dirname(slide.stillOut), { recursive: true });
          await page.screenshot({ path: slide.stillOut });
        }
        await page.waitForTimeout(slide.durationMs);
        const video = page.video();
        await context.close(); // видео дозаписывается только после close()
        const producedPath = await video.path();
        fs.mkdirSync(path.dirname(slide.videoOut), { recursive: true });
        fs.renameSync(producedPath, slide.videoOut);
        console.log('video:', slide.videoOut);
      } else {
        const context = await browser.newContext({
          viewport: { width: slide.width, height: slide.height },
          deviceScaleFactor: 2,
        });
        const page = await context.newPage();
        await page.goto(fileUrl);
        fs.mkdirSync(path.dirname(slide.out), { recursive: true });
        await page.screenshot({ path: slide.out });
        await context.close();
        console.log('png:', slide.out);
      }
    }
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
