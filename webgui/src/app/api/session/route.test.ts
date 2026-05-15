import { afterEach, describe, expect, it } from 'vitest';

import { WEBGUI_SESSION_COOKIE_NAME } from '../../../lib/http';
import { DELETE, GET, POST } from './route';

function sessionRequest(init?: RequestInit): Request {
  return new Request('http://localhost:3210/api/session', {
    ...init,
    headers: {
      origin: 'http://localhost:3210',
      ...(init?.headers || {}),
    },
  });
}

afterEach(() => {
  delete process.env.AGENTIC_TRADER_WEBGUI_TOKEN;
  delete process.env.AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY;
});

describe('session route', () => {
  it('reports whether a token is required', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY = '1';
    const openResponse = await GET(
      new Request('http://localhost:3210/api/session'),
    );
    expect(await openResponse.json()).toEqual({
      authenticated: true,
      tokenRequired: false,
    });

    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    const protectedResponse = await GET(
      new Request('http://localhost:3210/api/session'),
    );
    expect(await protectedResponse.json()).toEqual({
      authenticated: false,
      tokenRequired: true,
    });
  });

  it('sets and clears the HttpOnly session cookie', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';
    const login = await POST(
      sessionRequest({
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ token: 'local-token' }),
      }),
    );
    expect(login.status).toBe(200);
    expect(await login.json()).toEqual({
      authenticated: true,
      tokenRequired: true,
    });
    const cookie = login.headers.get('set-cookie') || '';
    expect(cookie).toContain(`${WEBGUI_SESSION_COOKIE_NAME}=local-token`);
    expect(cookie.toLowerCase()).toContain('httponly');
    expect(cookie.toLowerCase()).toContain('samesite=strict');

    const logout = await DELETE(sessionRequest({ method: 'DELETE' }));
    expect(logout.status).toBe(200);
    expect((logout.headers.get('set-cookie') || '').toLowerCase()).toContain(
      'max-age=0',
    );
  });

  it('rejects foreign, malformed, and wrong-token login attempts', async () => {
    process.env.AGENTIC_TRADER_WEBGUI_TOKEN = 'local-token';

    const foreign = await POST(
      new Request('http://localhost:3210/api/session', {
        method: 'POST',
        headers: {
          origin: 'http://evil.example',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ token: 'local-token' }),
      }),
    );
    expect(foreign.status).toBe(403);

    const wrongType = await POST(sessionRequest({ method: 'POST' }));
    expect(wrongType.status).toBe(400);

    const wrongToken = await POST(
      sessionRequest({
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ token: 'wrong-token' }),
      }),
    );
    expect(wrongToken.status).toBe(401);
  });
});
