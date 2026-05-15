import { NextResponse } from 'next/server';
import {
  WEBGUI_SESSION_COOKIE_NAME,
  configuredWebguiToken,
  constantTimeEqual,
  isAuthorizedWebguiRequest,
  isSameOriginRequest,
  parseJsonObjectBody,
  redactAndCapText,
} from '../../../lib/http';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

const MAX_SESSION_TOKEN_BYTES = 4 * 1024;
const SESSION_MAX_AGE_SECONDS = 12 * 60 * 60;

function sessionCookieOptions(request: Request) {
  return {
    httpOnly: true,
    maxAge: SESSION_MAX_AGE_SECONDS,
    path: '/',
    sameSite: 'strict' as const,
    secure: new URL(request.url).protocol === 'https:',
  };
}

function jsonError(error: string, status: number): Response {
  return Response.json({ error }, { status });
}

function rejectForeignSessionRequest(request: Request): null | Response {
  if (!isSameOriginRequest(request)) {
    return jsonError('forbidden origin', 403);
  }
  return null;
}

export async function GET(request: Request) {
  const tokenRequired = Boolean(configuredWebguiToken());
  return Response.json({
    authenticated: !tokenRequired || isAuthorizedWebguiRequest(request),
    tokenRequired,
  });
}

export async function POST(request: Request) {
  const unsafeResponse = rejectForeignSessionRequest(request);
  if (unsafeResponse) {
    return unsafeResponse;
  }
  const contentType = request.headers.get('content-type')?.toLowerCase() || '';
  if (!contentType.includes('application/json')) {
    return jsonError('expected application/json', 400);
  }

  const expectedToken = configuredWebguiToken();
  if (!expectedToken) {
    return Response.json({ authenticated: true, tokenRequired: false });
  }

  const parsed = await parseJsonObjectBody(request, {
    maxBytes: MAX_SESSION_TOKEN_BYTES,
  });
  if (!parsed.ok) {
    return parsed.response;
  }

  try {
    const providedToken = parsed.body.token;
    if (typeof providedToken !== 'string') {
      return jsonError('invalid token', 400);
    }
    const normalizedToken = providedToken.trim();
    if (
      !normalizedToken ||
      !constantTimeEqual(normalizedToken, expectedToken)
    ) {
      return jsonError('unauthorized', 401);
    }

    const response = NextResponse.json({
      authenticated: true,
      tokenRequired: true,
    });
    response.cookies.set({
      name: WEBGUI_SESSION_COOKIE_NAME,
      value: normalizedToken,
      ...sessionCookieOptions(request),
    });
    return response;
  } catch (error) {
    return jsonError(redactAndCapText(error), 500);
  }
}

export async function DELETE(request: Request) {
  const unsafeResponse = rejectForeignSessionRequest(request);
  if (unsafeResponse) {
    return unsafeResponse;
  }
  const response = NextResponse.json({ authenticated: false });
  response.cookies.set({
    name: WEBGUI_SESSION_COOKIE_NAME,
    value: '',
    ...sessionCookieOptions(request),
    maxAge: 0,
  });
  return response;
}
