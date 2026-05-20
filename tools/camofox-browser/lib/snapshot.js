/**
 * Snapshot windowing -- truncate large accessibility snapshots while
 * preserving pagination/navigation links at the tail.
 */

const MAX_SNAPSHOT_CHARS = 80000; // ~20K tokens
const SNAPSHOT_TAIL_CHARS = 5000; // keep last ~5K for pagination/nav links

/**
 * Produce a character-windowed view of a full snapshot YAML for pagination.
 *
 * When the snapshot is small enough, returns the full text; otherwise returns
 * a chunk of the snapshot plus a preserved tail and a truncation marker that
 * can be used to request the next window.
 *
 * @param {string} yaml - Full snapshot text to window; falsy values yield an empty result.
 * @param {number} [offset=0] - Starting character index within the snapshot for the returned chunk; clamped to a valid range so the tail is always preserved.
 * @returns {{text: string, truncated: boolean, totalChars: number, offset: number, hasMore?: boolean, nextOffset?: number|null}} An object describing the returned window:
 *  - `text`: the concatenated chunk, truncation marker (if any), and preserved tail.
 *  - `truncated`: `true` when the original snapshot was larger than the window and was truncated; `false` when the full snapshot is returned.
 *  - `totalChars`: total character length of the original `yaml`.
 *  - `offset`: the effective (clamped) offset used to produce the returned chunk.
 *  - `hasMore`: present when `truncated` is `true`; `true` if there is additional content (excluding the preserved tail) after this chunk.
 *  - `nextOffset`: the offset to pass to retrieve the next chunk when `hasMore` is `true`, otherwise `null`.
 */
function windowSnapshot(yaml, offset = 0) {
  if (!yaml) return { text: '', truncated: false, totalChars: 0, offset: 0 };
  const total = yaml.length;
  if (total <= MAX_SNAPSHOT_CHARS)
    return { text: yaml, truncated: false, totalChars: total, offset: 0 };

  const contentBudget = MAX_SNAPSHOT_CHARS - SNAPSHOT_TAIL_CHARS - 200; // room for marker
  const tail = yaml.slice(-SNAPSHOT_TAIL_CHARS);
  const clampedOffset = Math.min(
    Math.max(0, offset),
    total - SNAPSHOT_TAIL_CHARS,
  );
  const chunk = yaml.slice(clampedOffset, clampedOffset + contentBudget);
  const chunkEnd = clampedOffset + contentBudget;
  const hasMore = chunkEnd < total - SNAPSHOT_TAIL_CHARS;

  const marker = hasMore
    ? `\n[... truncated at char ${chunkEnd} of ${total}. Call snapshot with offset=${chunkEnd} to see more. Pagination links below. ...]\n`
    : '\n';

  return {
    text: chunk + marker + tail,
    truncated: true,
    totalChars: total,
    offset: clampedOffset,
    hasMore,
    nextOffset: hasMore ? chunkEnd : null,
  };
}

export { windowSnapshot, MAX_SNAPSHOT_CHARS, SNAPSHOT_TAIL_CHARS };
