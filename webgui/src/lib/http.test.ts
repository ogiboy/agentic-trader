import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  WEBGUI_SESSION_COOKIE_NAME,
  beginRequestGuard,
  configuredWebguiToken,
  constantTimeEqual,
  isAuthorizedWebguiRequest,
  isSameOriginRequest,
  parseJsonObjectBody,
  redactAndCapText,
  rejectUnsafeWebguiRequest,
  resetRequestGuardsForTests,
} from './http';

function request(url: string, init: RequestInit = {}): Request {
  return new Request(url, init);
}

afterEach(() => {
  vi.useRealTimers();
  resetRequestGuardsForTests();
  delete process.env.AGENTIC_TRADER_WEBGUI_TOKEN;
  delete process.env.AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY;
});

describe('webgui http guards', () => {
  it('authorizes header, bearer, and session cookie tokens in constant time', () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';

    expect(configuredWebguiToken()).toBe('local-token');
    expect(constantTimeEqual('local-token', 'local-token')).toBe(true);
    expect(constantTimeEqual('local-token', 'wrong-token')).toBe(false);
    expect(
      isAuthorizedWebguiRequest(
        request('http://localhost:3210/api/dashboard', {
          headers: { 'x-agentic-trader-token': 'local-token' },
        }),
      ),
    ).toBe(true);
    expect(
      isAuthorizedWebguiRequest(
        request('http://localhost:3210/api/dashboard', {
          headers: { authorization: 'Bearer local-token' },
        }),
      ),
    ).toBe(true);
    expect(
      isAuthorizedWebguiRequest(
        request('http://localhost:3210/api/dashboard', {
          headers: {
            cookie: `${WEBGUI_SESSION_COOKIE_NAME}=local-token`,
          },
        }),
      ),
    ).toBe(true);
  });

  it('allows tokenless loopback only when explicitly enabled', () => {
    expect(
      isAuthorizedWebguiRequest(request('http://localhost:3210/api/dashboard')),
    ).toBe(false);

    process.env.AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY = '1';
    expect(
      isAuthorizedWebguiRequest(request('http://localhost:3210/api/dashboard')),
    ).toBe(true);
    expect(
      isAuthorizedWebguiRequest(request('http://example.com/api/dashboard')),
    ).toBe(false);
  });

  it('accepts same-origin and loopback-equivalent browser requests', () => {
    expect(
      isSameOriginRequest(
        request('http://127.0.0.1:3210/api/dashboard', {
          headers: { origin: 'http://localhost:3210' },
        }),
      ),
    ).toBe(true);
    expect(
      isSameOriginRequest(
        request('http://localhost:3210/api/dashboard', {
          headers: { referer: 'http://evil.example/dashboard' },
        }),
      ),
    ).toBe(false);
    expect(
      isSameOriginRequest(request('http://localhost:3210/api/dashboard')),
    ).toBe(true);
    expect(
      isSameOriginRequest(
        request('http://localhost:3210/api/dashboard', { method: 'POST' }),
      ),
    ).toBe(false);
  });

  it('rejects unsafe requests before route handlers run', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    const unauthorized = rejectUnsafeWebguiRequest(
      request('http://localhost:3210/api/runtime', {
        method: 'POST',
        headers: { origin: 'http://localhost:3210' },
      }),
      { requireJson: true },
    );
    expect(unauthorized?.status).toBe(401);

    const wrongType = rejectUnsafeWebguiRequest(
      request('http://localhost:3210/api/runtime', {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3210',
          'x-agentic-trader-token': 'local-token',
        },
      }),
      { requireJson: true },
    );
    expect(wrongType?.status).toBe(400);
    expect(await wrongType?.json()).toEqual({
      error: 'expected application/json',
    });
  });

  it('limits and parses JSON object bodies', async () => {
    const parsed = await parseJsonObjectBody(
      request('http://localhost:3210/api/runtime', {
        method: 'POST',
        body: JSON.stringify({ kind: 'start' }),
      }),
    );
    expect(parsed.ok && parsed.body.kind).toBe('start');

    const arrayBody = await parseJsonObjectBody(
      request('http://localhost:3210/api/runtime', {
        method: 'POST',
        body: '[]',
      }),
    );
    expect(arrayBody.ok).toBe(false);

    const tooLarge = await parseJsonObjectBody(
      request('http://localhost:3210/api/runtime', {
        method: 'POST',
        headers: { 'content-length': '999' },
        body: '{}',
      }),
      { maxBytes: 2 },
    );
    expect(tooLarge.ok).toBe(false);
    expect(!tooLarge.ok && tooLarge.response.status).toBe(413);

    const chunkedTooLarge = await parseJsonObjectBody(
      request('http://localhost:3210/api/runtime', {
        method: 'POST',
        body: JSON.stringify({ note: 'x'.repeat(32) }),
      }),
      { maxBytes: 8 },
    );
    expect(chunkedTooLarge.ok).toBe(false);
    expect(!chunkedTooLarge.ok && chunkedTooLarge.response.status).toBe(413);
  });

  it('rate limits and single-flights guarded requests', async () => {
    vi.useFakeTimers();
    const first = beginRequestGuard({
      key: 'node-test-guard',
      singleFlight: true,
    });
    expect(first.ok).toBe(true);
    const duplicate = beginRequestGuard({
      key: 'node-test-guard',
      singleFlight: true,
    });
    expect(duplicate.ok).toBe(false);
    expect(!duplicate.ok && duplicate.response.status).toBe(409);
    if (first.ok) {
      first.release();
    }

    const cooldown = beginRequestGuard({
      cooldownMs: 2_000,
      key: 'node-test-cooldown',
      singleFlight: true,
    });
    expect(cooldown.ok).toBe(true);
    if (cooldown.ok) {
      cooldown.release();
    }
    const limited = beginRequestGuard({ key: 'node-test-cooldown' });
    expect(limited.ok).toBe(false);
    expect(!limited.ok && limited.response.headers.get('Retry-After')).toBe(
      '2',
    );
  });

  it('redacts common secret shapes and caps long errors', () => {
    process.env.AGENTIC_TRADER_TEST_SECRET = 'raw-secret-value';
    const text = redactAndCapText(
      'API_KEY=abc Bearer token123 Authorization: raw https://x.test?a=1&token=abc {"api_key":"json-secret"} raw-secret-value',
      500,
    );
    expect(text).toContain('API_KEY=<redacted>');
    expect(text).toContain('Bearer <redacted>');
    expect(text).toContain('"api_key":"<redacted>"');
    expect(text).not.toContain('raw-secret-value');
    expect(redactAndCapText('x'.repeat(80), 40)).toContain('...<truncated>');
  });
});
