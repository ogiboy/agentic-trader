const ALLOWED_URL_SCHEMES = ['http:', 'https:'];

export function createRouteSafety({ config, log, StaleRefsError }) {
  function safeError(err) {
    if (config.nodeEnv === 'production') {
      log('error', 'internal error', { error: err.message, stack: err.stack });
      return 'Internal server error';
    }
    return err.message;
  }

  function sendError(res, err, extraFields = {}) {
    const status = err instanceof StaleRefsError ? 422 : err.statusCode || 500;
    const body = { error: safeError(err), ...extraFields };
    if (err instanceof StaleRefsError) {
      body.code = 'stale_refs';
      body.ref = err.ref;
    }
    res.status(status).json(body);
  }

  function validateUrl(url) {
    try {
      const parsed = new URL(url);
      if (!ALLOWED_URL_SCHEMES.includes(parsed.protocol)) {
        return `Blocked URL scheme: ${parsed.protocol} (only http/https allowed)`;
      }
      return null;
    } catch {
      return `Invalid URL: ${url}`;
    }
  }

  return { safeError, sendError, validateUrl };
}
