export function createPageReadiness({ log }) {
  async function waitForPageReady(page, options = {}) {
    const {
      timeout = 10000,
      waitForNetwork = true,
      waitForHydration = true,
      settleMs = 200,
      hydrationPollMs = 250,
      hydrationTimeoutMs = Math.min(timeout, 10000),
    } = options;

    try {
      await page.waitForLoadState('domcontentloaded', { timeout });

      if (waitForNetwork) {
        await page
          .waitForLoadState('networkidle', { timeout: 5000 })
          .catch(() => {
            log('warn', 'networkidle timeout, continuing');
          });
      }

      if (waitForHydration) {
        const maxIterations = Math.max(
          1,
          Math.floor(hydrationTimeoutMs / hydrationPollMs),
        );
        await page
          .evaluate(
            async ({ maxIterations, hydrationPollMs }) => {
              for (let i = 0; i < maxIterations; i++) {
                const entries = performance.getEntriesByType('resource');
                const recentEntries = entries.slice(-5);
                const netQuiet = recentEntries.every(
                  (e) => performance.now() - e.responseEnd > 400,
                );

                if (document.readyState === 'complete' && netQuiet) {
                  await new Promise((r) =>
                    requestAnimationFrame(() => requestAnimationFrame(r)),
                  );
                  break;
                }
                await new Promise((r) => setTimeout(r, hydrationPollMs));
              }
            },
            { maxIterations, hydrationPollMs },
          )
          .catch(() => {
            log('warn', 'hydration wait failed, continuing');
          });
      }

      if (settleMs > 0) {
        await page.waitForTimeout(settleMs);
      }

      await dismissConsentDialogs(page);
      return true;
    } catch (err) {
      log('warn', 'page ready failed', { error: err.message });
      return false;
    }
  }

  async function dismissConsentDialogs(page) {
    const dismissSelectors = [
      '#onetrust-banner-sdk button#onetrust-accept-btn-handler',
      '#onetrust-banner-sdk button#onetrust-reject-all-handler',
      '#onetrust-close-btn-container button',
      'button[data-test="cookie-accept-all"]',
      'button[aria-label="Accept all"]',
      'button[aria-label="Accept All"]',
      'button[aria-label="Close"]',
      'button[aria-label="Dismiss"]',
      'dialog button:has-text("Close")',
      'dialog button:has-text("Accept")',
      'dialog button:has-text("I Accept")',
      'dialog button:has-text("Got it")',
      'dialog button:has-text("OK")',
      '[class*="consent"] button[class*="accept"]',
      '[class*="consent"] button[class*="close"]',
      '[class*="privacy"] button[class*="close"]',
      '[class*="cookie"] button[class*="accept"]',
      '[class*="cookie"] button[class*="close"]',
      '[class*="modal"] button[class*="close"]',
      '[class*="overlay"] button[class*="close"]',
    ];

    for (const selector of dismissSelectors) {
      try {
        const button = page.locator(selector).first();
        if (await button.isVisible({ timeout: 100 })) {
          await button.click({ timeout: 1000 }).catch(() => {});
          log('info', 'dismissed consent dialog', { selector });
          await page.waitForTimeout(300);
          break;
        }
      } catch {
        // Selector not found or not clickable.
      }
    }
  }

  return { dismissConsentDialogs, waitForPageReady };
}
