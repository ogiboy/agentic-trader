function defaultKeyGenerator(req) {
  return req.ip || req.socket?.remoteAddress || 'unknown';
}

/**
 * Create a small in-process Express rate-limit middleware.
 */
function rateLimit({
  windowMs = 60_000,
  max = 60,
  keyPrefix = 'global',
  keyGenerator = defaultKeyGenerator,
  now = () => Date.now(),
} = {}) {
  const hits = new Map();

  return function rateLimitMiddleware(req, res, next) {
    const nowMs = now();
    const key = `${keyPrefix}:${keyGenerator(req)}`;
    let state = hits.get(key);
    if (!state || nowMs >= state.resetAt) {
      state = { count: 0, resetAt: nowMs + windowMs };
    }

    state.count += 1;
    hits.set(key, state);

    if (state.count > max) {
      const retryAfterSeconds = Math.max(
        1,
        Math.ceil((state.resetAt - nowMs) / 1000),
      );
      return res
        .status(429)
        .set('Retry-After', String(retryAfterSeconds))
        .json({ error: 'Too many requests' });
    }

    return next();
  };
}

export { rateLimit };
