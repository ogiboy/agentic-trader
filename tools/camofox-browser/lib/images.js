/**
 * In-page image extraction via Playwright page.evaluate().
 *
 * Separated from downloads.js to keep file I/O and image extraction concerns apart.
 * (browser-side fetch inside page.evaluate + Node fs reads in same file).
 */

import { MAX_DOWNLOAD_INLINE_BYTES } from './downloads.js';

/**
 * Collects metadata for visible <img> elements on the given page and optionally fetches & inlines image bytes.
 * @param {import('playwright').Page} page - Playwright page used to inspect the document.
 * @param {Object} [options]
 * @param {boolean} [options.includeData=false] - If `true`, attempts to fetch or inline image data for each image.
 * @param {number} [options.maxBytes=MAX_DOWNLOAD_INLINE_BYTES] - Maximum byte size allowed for inlining image data; larger images will be skipped and marked with `dataSkipped: 'max_bytes_exceeded'`.
 * @param {number} [options.limit=8] - Maximum number of unique images to consider.
 * @returns {Array<Object>} An array of image entries. Each entry always contains `src`, `alt`, `width`, and `height`. When `includeData` is `true`, entries may also include:
 * - `mimeType`: reported MIME type for the image (string).
 * - `bytes`: estimated or actual byte size (number).
 * - `dataUrl`: a data URL with the inlined image when `bytes <= maxBytes` (string).
 * - `dataSkipped`: set to `'max_bytes_exceeded'` when data was not inlined due to size (string).
 * - `fetchError`: error identifier or message when fetching/conversion failed (string).
 */
async function extractPageImages(
  page,
  { includeData = false, maxBytes = MAX_DOWNLOAD_INLINE_BYTES, limit = 8 } = {},
) {
  return page.evaluate(
    async ({ includeData, maxBytes, limit }) => {
      const toDataUrl = (blob) =>
        new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () =>
            resolve(typeof reader.result === 'string' ? reader.result : '');
          reader.onerror = () => reject(new Error('file_reader_failed'));
          reader.readAsDataURL(blob);
        });

      const nodes = Array.from(document.querySelectorAll('img'));
      const seen = new Set();
      const candidates = [];

      for (const node of nodes) {
        const src = String(
          node.currentSrc || node.src || node.getAttribute('src') || '',
        ).trim();
        if (!src || seen.has(src)) continue;
        seen.add(src);
        candidates.push({
          src,
          alt: String(node.alt || '').trim(),
          width: Number(node.naturalWidth || node.width || 0) || undefined,
          height: Number(node.naturalHeight || node.height || 0) || undefined,
        });
        if (candidates.length >= limit) break;
      }

      const results = [];
      for (const image of candidates) {
        const entry = {
          src: image.src,
          alt: image.alt,
          width: image.width,
          height: image.height,
        };

        if (includeData) {
          try {
            if (image.src.startsWith('data:')) {
              const mimeMatch = image.src.match(/^data:([^;,]+)[;,]/i);
              const isBase64 = /;base64,/i.test(image.src);
              const payload = image.src.slice(image.src.indexOf(',') + 1);
              const estimatedBytes = isBase64
                ? Math.floor((payload.length * 3) / 4)
                : payload.length;
              entry.mimeType = mimeMatch
                ? mimeMatch[1]
                : 'application/octet-stream';
              entry.bytes = estimatedBytes;
              if (estimatedBytes <= maxBytes) {
                entry.dataUrl = image.src;
              } else {
                entry.dataSkipped = 'max_bytes_exceeded';
              }
            } else {
              const response = await fetch(image.src, {
                credentials: 'include',
              });
              if (response.ok) {
                const blob = await response.blob();
                entry.mimeType = blob.type || 'application/octet-stream';
                entry.bytes = blob.size;
                if (blob.size <= maxBytes) {
                  entry.dataUrl = await toDataUrl(blob);
                } else {
                  entry.dataSkipped = 'max_bytes_exceeded';
                }
              } else {
                entry.fetchError = `http_${response.status}`;
              }
            }
          } catch (err) {
            entry.fetchError = String(
              err?.message || err || 'image_fetch_failed',
            );
          }
        }

        results.push(entry);
      }

      return results;
    },
    { includeData, maxBytes, limit },
  );
}

export { extractPageImages };
