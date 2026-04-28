import type { Metadata } from 'next';

function normalizeBasePath(value: string | undefined) {
  const trimmed = (value ?? '').trim().replace(/\/+$/g, '');
  if (!trimmed) return '';
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

export const basePath = normalizeBasePath(process.env.NEXT_PUBLIC_BASE_PATH);

const assetPath = (path: `/${string}`) => `${basePath}${path}`;

export const docsMetadata: Metadata = {
  title: {
    default: 'Agentic Trader Docs',
    template: '%s | Agentic Trader Docs',
  },
  description:
    'Developer documentation for the local-first Agentic Trader runtime, operator surfaces, and QA workflow.',

  icons: {
    shortcut: assetPath('/favicon.ico'),
    apple: assetPath('/apple-touch-icon.png'),
    icon: [
      {
        url: assetPath('/favicon-16x16.png'),
        sizes: '16x16',
        type: 'image/png',
      },
      {
        url: assetPath('/favicon-32x32.png'),
        sizes: '32x32',
        type: 'image/png',
      },
    ],
  },
  manifest: assetPath('/site.webmanifest'),
};
