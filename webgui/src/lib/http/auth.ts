import { timingSafeEqual } from 'node:crypto';

import { jsonError } from './responses';

const SAFE_METHODS_WITHOUT_BROWSER_ORIGIN = new Set(['GET', 'HEAD', 'OPTIONS']);

export const WEBGUI_SESSION_COOKIE_NAME = 'agentic_trader_webgui_session';

export function configuredWebguiToken(): null | string {
  const token = process.env.AGENTIC_TRADER_WEBGUI_TOKEN?.trim();
  return token || null;
}

function tokenlessLoopbackModeEnabled(): boolean {
  return process.env.AGENTIC_TRADER_WEBGUI_LOOPBACK_ONLY === '1';
}

export function constantTimeEqual(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  if (leftBuffer.length !== rightBuffer.length) {
    return false;
  }
  return timingSafeEqual(leftBuffer, rightBuffer);
}

function bearerToken(value: null | string): null | string {
  const prefix = 'Bearer ';
  if (!value?.startsWith(prefix)) {
    return null;
  }
  return value.slice(prefix.length).trim() || null;
}

function isLoopbackHostname(hostname: string): boolean {
  const normalized = hostname.toLowerCase().replaceAll(/^\[|\]$/g, '');
  return (
    normalized === 'localhost' ||
    normalized === '127.0.0.1' ||
    normalized === '::1' ||
    normalized.endsWith('.localhost')
  );
}

function originPort(url: URL): string {
  if (url.port) {
    return url.port;
  }
  if (url.protocol === 'https:') {
    return '443';
  }
  if (url.protocol === 'http:') {
    return '80';
  }
  return '';
}

function isEquivalentSameOrigin(left: URL, right: URL): boolean {
  if (left.origin === right.origin) {
    return true;
  }
  return (
    left.protocol === right.protocol &&
    originPort(left) === originPort(right) &&
    isLoopbackHostname(left.hostname) &&
    isLoopbackHostname(right.hostname)
  );
}

function cookieValue(request: Request, cookieName: string): null | string {
  const rawCookie = request.headers.get('cookie');
  if (!rawCookie) {
    return null;
  }
  for (const chunk of rawCookie.split(';')) {
    const [name, ...valueParts] = chunk.trim().split('=');
    if (name !== cookieName) {
      continue;
    }
    const rawValue = valueParts.join('=');
    if (!rawValue) {
      return null;
    }
    try {
      return decodeURIComponent(rawValue);
    } catch {
      return rawValue;
    }
  }
  return null;
}

export function isAuthorizedWebguiRequest(request: Request): boolean {
  const token = configuredWebguiToken();
  const requestUrl = new URL(request.url);
  if (!token) {
    return (
      tokenlessLoopbackModeEnabled() && isLoopbackHostname(requestUrl.hostname)
    );
  }
  const provided =
    request.headers.get('x-agentic-trader-token') ||
    bearerToken(request.headers.get('authorization')) ||
    cookieValue(request, WEBGUI_SESSION_COOKIE_NAME) ||
    '';
  return constantTimeEqual(provided, token);
}

export function isSameOriginRequest(request: Request): boolean {
  const requestUrl = new URL(request.url);
  const origin = request.headers.get('origin');
  if (origin) {
    try {
      return isEquivalentSameOrigin(new URL(origin), requestUrl);
    } catch {
      return false;
    }
  }
  const referer = request.headers.get('referer');
  if (!referer) {
    return SAFE_METHODS_WITHOUT_BROWSER_ORIGIN.has(
      request.method.toUpperCase(),
    );
  }
  try {
    return isEquivalentSameOrigin(new URL(referer), requestUrl);
  } catch {
    return false;
  }
}

export function rejectUnsafeWebguiRequest(
  request: Request,
  { requireJson }: { requireJson: boolean },
): null | Response {
  if (!isAuthorizedWebguiRequest(request)) {
    return jsonError('unauthorized', 401);
  }
  if (!isSameOriginRequest(request)) {
    return jsonError('forbidden origin', 403);
  }
  if (requireJson) {
    const contentType =
      request.headers.get('content-type')?.toLowerCase() || '';
    if (!contentType.includes('application/json')) {
      return jsonError('expected application/json', 400);
    }
  }
  return null;
}
