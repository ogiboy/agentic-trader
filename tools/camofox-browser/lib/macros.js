const MACROS = {
  '@google_search': (query) =>
    `https://www.google.com/search?q=${encodeURIComponent(query || '')}`,
  '@youtube_search': (query) =>
    `https://www.youtube.com/results?search_query=${encodeURIComponent(query || '')}`,
  '@amazon_search': (query) =>
    `https://www.amazon.com/s?k=${encodeURIComponent(query || '')}`,
  '@reddit_search': (query) =>
    `https://www.reddit.com/search.json?q=${encodeURIComponent(query || '')}&limit=25`,
  '@reddit_subreddit': (query) =>
    `https://www.reddit.com/r/${encodeURIComponent(query || 'all')}.json?limit=25`,
  '@wikipedia_search': (query) =>
    `https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(query || '')}`,
  '@twitter_search': (query) =>
    `https://twitter.com/search?q=${encodeURIComponent(query || '')}`,
  '@yelp_search': (query) =>
    `https://www.yelp.com/search?find_desc=${encodeURIComponent(query || '')}`,
  '@spotify_search': (query) =>
    `https://open.spotify.com/search/${encodeURIComponent(query || '')}`,
  '@netflix_search': (query) =>
    `https://www.netflix.com/search?q=${encodeURIComponent(query || '')}`,
  '@linkedin_search': (query) =>
    `https://www.linkedin.com/search/results/all/?keywords=${encodeURIComponent(query || '')}`,
  '@instagram_search': (query) =>
    `https://www.instagram.com/explore/tags/${encodeURIComponent(query || '')}`,
  '@tiktok_search': (query) =>
    `https://www.tiktok.com/search?q=${encodeURIComponent(query || '')}`,
  '@twitch_search': (query) =>
    `https://www.twitch.tv/search?term=${encodeURIComponent(query || '')}`,
};

/**
 * Return the URL produced by a named macro or `null` if the macro is not supported.
 * @param {string} macro - Macro identifier (for example, "@google_search" or "@reddit_subreddit").
 * @param {string} [query] - Query string passed to the macro; may be omitted or undefined.
 * @returns {string|null} The expanded URL for the given macro and query, or `null` when the macro key is unknown.
 */
function expandMacro(macro, query) {
  const macroFn = MACROS[macro];
  return macroFn ? macroFn(query) : null;
}

/**
 * Retrieve the supported macro keys.
 * @returns {string[]} An array of supported macro key strings (e.g., "@google_search").
 */
function getSupportedMacros() {
  return Object.keys(MACROS);
}

export { expandMacro, getSupportedMacros, MACROS };
