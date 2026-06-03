export function createGoogleSerpHelpers({ log }) {
  function isGoogleSerp(url) {
    try {
      const parsed = new URL(url);
      return (
        parsed.hostname.includes('google.') && parsed.pathname === '/search'
      );
    } catch {
      return false;
    }
  }

  function isGoogleSearchUrl(url) {
    try {
      const parsed = new URL(url);
      return (
        parsed.hostname.includes('google.') && parsed.pathname === '/search'
      );
    } catch {
      return false;
    }
  }

  async function isGoogleSearchBlocked(page) {
    if (!page || page.isClosed()) return false;

    const url = page.url();
    if (url.includes('google.com/sorry/')) return true;

    const bodyText = await page
      .evaluate(() => document.body?.innerText?.slice(0, 600) || '')
      .catch(() => '');
    return /Our systems have detected unusual traffic|About this page|If you're having trouble accessing Google Search|SG_REL/.test(
      bodyText,
    );
  }

  /**
   * Extract structured refs and a readable snapshot from Google Search results.
   *
   * @param {import('playwright').Page} page
   * @returns {{ refs: Map<string, {role: string, name: string, nth: number}>, snapshot: string }}
   */
  async function extractGoogleSerp(page) {
    const refs = new Map();
    if (!page || page.isClosed()) return { refs, snapshot: '' };

    const start = Date.now();

    const alreadyRendered = await page
      .evaluate(
        () =>
          !!document.querySelector('#rso h3, #search h3, #rso [data-snhf]'),
      )
      .catch(() => false);
    if (!alreadyRendered) {
      try {
        await page.waitForSelector('#rso h3, #search h3, #rso [data-snhf]', {
          timeout: 5000,
        });
      } catch {
        try {
          await page.waitForSelector(
            '#rso a[href]:not([href^="/search"]), #search a[href]:not([href^="/search"])',
            { timeout: 2000 },
          );
        } catch {}
      }
    }

    const extracted = await page.evaluate(() => {
      const snapshot = [];
      const elements = [];
      let refCounter = 1;

      function addRef(role, name) {
        const id = 'e' + refCounter++;
        elements.push({ id, role, name });
        return id;
      }

      snapshot.push(
        '- heading "' + document.title.replaceAll('"', String.raw`\"`) + '"',
      );

      const searchInput = document.querySelector(
        'input[name="q"], textarea[name="q"]',
      );
      if (searchInput) {
        const name = 'Search';
        const refId = addRef('searchbox', name);
        snapshot.push(
          '- searchbox "' +
            name +
            '" [' +
            refId +
            ']: ' +
            (searchInput.value || ''),
        );
      }

      const navContainer = document.querySelector(
        'div[role="navigation"], div[role="list"]',
      );
      if (navContainer) {
        const navLinks = navContainer.querySelectorAll('a');
        if (navLinks.length > 0) {
          snapshot.push('- navigation:');
          navLinks.forEach((a) => {
            const text = (a.textContent || '').trim();
            if (!text || text.length < 1) return;
            if (/^\d+$/.test(text) && Number.parseInt(text) < 50) return;
            const refId = addRef('link', text);
            snapshot.push('  - link "' + text + '" [' + refId + ']');
          });
        }
      }

      const resultContainer =
        document.querySelector('#rso') || document.querySelector('#search');
      if (resultContainer) {
        const resultBlocks = resultContainer.querySelectorAll(':scope > div');
        for (const block of resultBlocks) {
          const h3 = block.querySelector('h3');
          const mainLink = h3 ? h3.closest('a') : null;

          if (h3 && mainLink) {
            const title = h3.textContent
              .trim()
              .replaceAll('"', String.raw`\"`);
            const href = mainLink.href;
            const cite = block.querySelector('cite');
            const displayUrl = cite ? cite.textContent.trim() : '';

            let snippet = '';
            for (const selector of [
              '[data-sncf]',
              '[data-content-feature="1"]',
              '.VwiC3b',
              'div[style*="-webkit-line-clamp"]',
              'span.aCOpRe',
            ]) {
              const el = block.querySelector(selector);
              if (el) {
                snippet = el.textContent.trim().slice(0, 300);
                break;
              }
            }
            if (!snippet) {
              const allText = block.textContent.trim().replace(/\s+/g, ' ');
              const titleLen =
                title.length + (displayUrl ? displayUrl.length : 0);
              if (allText.length > titleLen + 20) {
                snippet = allText.slice(titleLen).trim().slice(0, 300);
              }
            }

            const refId = addRef('link', title);
            snapshot.push(
              '- link "' + title + '" [' + refId + ']:',
              '  - /url: ' + href,
            );
            if (displayUrl) snapshot.push('  - cite: ' + displayUrl);
            if (snippet) snapshot.push('  - text: ' + snippet);
          } else {
            const blockLinks = block.querySelectorAll(
              'a[href^="http"]:not([href*="google.com/search"])',
            );
            if (blockLinks.length > 0) {
              const blockText = block.textContent
                .trim()
                .replace(/\s+/g, ' ')
                .slice(0, 200);
              if (blockText.length > 10) {
                snapshot.push('- group:', '  - text: ' + blockText);
                blockLinks.forEach((a) => {
                  const linkText = (a.textContent || '')
                    .trim()
                    .replaceAll('"', String.raw`\"`)
                    .slice(0, 100);
                  if (linkText.length > 2) {
                    const refId = addRef('link', linkText);
                    snapshot.push(
                      '  - link "' + linkText + '" [' + refId + ']:',
                      '    - /url: ' + a.href,
                    );
                  }
                });
              }
            }
          }
        }
      }

      const paaItems = document.querySelectorAll(
        '[jsname="Cpkphb"], div.related-question-pair',
      );
      if (paaItems.length > 0) {
        snapshot.push('- heading "People also ask"');
        paaItems.forEach((q) => {
          const text = (q.textContent || '')
            .trim()
            .replaceAll('"', String.raw`\"`)
            .slice(0, 150);
          if (text) {
            const refId = addRef('button', text);
            snapshot.push('  - button "' + text + '" [' + refId + ']');
          }
        });
      }

      const nextLink = document.querySelector(
        '#botstuff a[aria-label="Next page"], td.d6cvqb a, a#pnnext',
      );
      if (nextLink) {
        const refId = addRef('link', 'Next');
        snapshot.push(
          '- navigation "pagination":',
          '  - link "Next" [' + refId + ']',
        );
      }

      return { snapshot: snapshot.join('\n'), elements };
    });

    const seenCounts = new Map();
    for (const el of extracted.elements) {
      const key = `${el.role}:${el.name}`;
      const nth = seenCounts.get(key) || 0;
      seenCounts.set(key, nth + 1);
      refs.set(el.id, { role: el.role, name: el.name, nth });
    }

    log('info', 'extractGoogleSerp', {
      elapsed: Date.now() - start,
      refs: refs.size,
    });
    return { refs, snapshot: extracted.snapshot };
  }

  return {
    extractGoogleSerp,
    isGoogleSearchBlocked,
    isGoogleSearchUrl,
    isGoogleSerp,
  };
}
