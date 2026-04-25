import { NextResponse, type NextRequest } from 'next/server';

import { getDocLanguage } from '@/lib/i18n/routing';

const DOC_LANGUAGE_HEADER = 'x-agentic-doc-lang';

export function proxy(request: NextRequest) {
  const firstSegment = request.nextUrl.pathname.split('/').filter(Boolean)[0];
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set(DOC_LANGUAGE_HEADER, getDocLanguage(firstSegment));

  return NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
