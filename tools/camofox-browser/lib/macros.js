const MACRO_EXPANDERS = Object.freeze({
  googleSearch: (query) =>
    `https://www.google.com/search?q=${encodeURIComponent(query || '')}`,
  youtubeSearch: (query) =>
    `https://www.youtube.com/results?search_query=${encodeURIComponent(query || '')}`,
  amazonSearch: (query) =>
    `https://www.amazon.com/s?k=${encodeURIComponent(query || '')}`,
  redditSearch: (query) =>
    `https://www.reddit.com/search.json?q=${encodeURIComponent(query || '')}&limit=25`,
  redditSubreddit: (query) =>
    `https://www.reddit.com/r/${encodeURIComponent(query || 'all')}.json?limit=25`,
  wikipediaSearch: (query) =>
    `https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(query || '')}`,
  twitterSearch: (query) =>
    `https://twitter.com/search?q=${encodeURIComponent(query || '')}`,
  yelpSearch: (query) =>
    `https://www.yelp.com/search?find_desc=${encodeURIComponent(query || '')}`,
  spotifySearch: (query) =>
    `https://open.spotify.com/search/${encodeURIComponent(query || '')}`,
  netflixSearch: (query) =>
    `https://www.netflix.com/search?q=${encodeURIComponent(query || '')}`,
  linkedinSearch: (query) =>
    `https://www.linkedin.com/search/results/all/?keywords=${encodeURIComponent(query || '')}`,
  instagramSearch: (query) =>
    `https://www.instagram.com/explore/tags/${encodeURIComponent(query || '')}`,
  tiktokSearch: (query) =>
    `https://www.tiktok.com/search?q=${encodeURIComponent(query || '')}`,
  twitchSearch: (query) =>
    `https://www.twitch.tv/search?term=${encodeURIComponent(query || '')}`,
});

const MACROS = Object.freeze({
  '@google_search': MACRO_EXPANDERS.googleSearch,
  '@youtube_search': MACRO_EXPANDERS.youtubeSearch,
  '@amazon_search': MACRO_EXPANDERS.amazonSearch,
  '@reddit_search': MACRO_EXPANDERS.redditSearch,
  '@reddit_subreddit': MACRO_EXPANDERS.redditSubreddit,
  '@wikipedia_search': MACRO_EXPANDERS.wikipediaSearch,
  '@twitter_search': MACRO_EXPANDERS.twitterSearch,
  '@yelp_search': MACRO_EXPANDERS.yelpSearch,
  '@spotify_search': MACRO_EXPANDERS.spotifySearch,
  '@netflix_search': MACRO_EXPANDERS.netflixSearch,
  '@linkedin_search': MACRO_EXPANDERS.linkedinSearch,
  '@instagram_search': MACRO_EXPANDERS.instagramSearch,
  '@tiktok_search': MACRO_EXPANDERS.tiktokSearch,
  '@twitch_search': MACRO_EXPANDERS.twitchSearch,
});

/**
 * Return the URL produced by a named macro or `null` if the macro is not supported.
 * @param {string} macro - Macro identifier (for example, "@google_search" or "@reddit_subreddit").
 * @param {string} [query] - Query string passed to the macro; may be omitted or undefined.
 * @returns {string|null} The expanded URL for the given macro and query, or `null` when the macro key is unknown.
 */
function expandMacro(macro, query) {
  switch (macro) {
    case '@google_search':
      return MACRO_EXPANDERS.googleSearch(query);
    case '@youtube_search':
      return MACRO_EXPANDERS.youtubeSearch(query);
    case '@amazon_search':
      return MACRO_EXPANDERS.amazonSearch(query);
    case '@reddit_search':
      return MACRO_EXPANDERS.redditSearch(query);
    case '@reddit_subreddit':
      return MACRO_EXPANDERS.redditSubreddit(query);
    case '@wikipedia_search':
      return MACRO_EXPANDERS.wikipediaSearch(query);
    case '@twitter_search':
      return MACRO_EXPANDERS.twitterSearch(query);
    case '@yelp_search':
      return MACRO_EXPANDERS.yelpSearch(query);
    case '@spotify_search':
      return MACRO_EXPANDERS.spotifySearch(query);
    case '@netflix_search':
      return MACRO_EXPANDERS.netflixSearch(query);
    case '@linkedin_search':
      return MACRO_EXPANDERS.linkedinSearch(query);
    case '@instagram_search':
      return MACRO_EXPANDERS.instagramSearch(query);
    case '@tiktok_search':
      return MACRO_EXPANDERS.tiktokSearch(query);
    case '@twitch_search':
      return MACRO_EXPANDERS.twitchSearch(query);
    default:
      return null;
  }
}

/**
 * Retrieve the supported macro keys.
 * @returns {string[]} An array of supported macro key strings (e.g., "@google_search").
 */
function getSupportedMacros() {
  return Object.keys(MACROS);
}

export { expandMacro, getSupportedMacros, MACROS };
