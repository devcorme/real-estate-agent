import { test } from '@playwright/test';

test('scrape apartments', async ({ page }) => {
  await page.goto('https://patuljak.me/c/stanovi');
  
  // Wait for any card to appear with a timeout
  try {
    await page.waitForSelector('.card-body', { timeout: 5000 });
  } catch (e) {
    console.log('Timeout waiting for cards, trying to continue anyway...');
  }
  
  // Wait a bit for dynamic content
  await page.waitForTimeout(2000);
  
  // Try different selector strategies
  const links = await page.locator('a').filter({ hasText: /stan/i }).all();
  
  console.log('Found links:', links.length);

  for (const link of links) {
    const href = await link.getAttribute('href');
    console.log('Found href:', href);
    if (href?.includes('/oglas/')) {
      const title = await link.textContent();
      console.log('Processing:', { href, title });
      
      if (href) {
        const fullUrl = `https://patuljak.me${href}`;
        console.log('Visiting:', { title, url: fullUrl });
        
        const newPage = await page.context().newPage();
        await newPage.goto(fullUrl);
        await newPage.waitForLoadState('networkidle');
        await newPage.screenshot({ path: `apartment-${href.split('/').pop()}.png` });
        await newPage.close();
      }
    }
  }
});
