'use strict';

import type { Metadata } from 'next';
import localFont from 'next/font/local';
import { getLocale } from 'next-intl/server';
import { ControlRoomIntlProvider } from '@/i18n/ControlRoomIntlProvider';
import { normalizeWebguiLocale } from '@/i18n/locales';
import './globals.css';
import { WEBGUI_SITE_METADATA } from './site-metadata';

const jetBrainsMono = localFont({
  src: [
    {
      path: './fonts/JetBrainsMonoVariable.ttf',
      weight: '100 800',
      style: 'normal',
    },
    {
      path: './fonts/JetBrainsMonoItalicVariable.ttf',
      weight: '100 800',
      style: 'italic',
    },
  ],
  variable: '--font-jetbrains-mono',
  display: 'swap',
  fallback: [
    'ui-monospace',
    'SFMono-Regular',
    'Menlo',
    'Monaco',
    'Consolas',
    'Liberation Mono',
    'monospace',
  ],
});

export const metadata: Metadata = {
  title: WEBGUI_SITE_METADATA.title,
  description: WEBGUI_SITE_METADATA.description,
  icons: {
    shortcut: '/favicon.ico',
    apple: '/apple-touch-icon.png',
    icon: [
      {
        url: '/favicon-16x16.png',
        sizes: '16x16',
        type: 'image/png',
      },
      {
        url: '/favicon-32x32.png',
        sizes: '32x32',
        type: 'image/png',
      },
    ],
  },
  manifest: '/site.webmanifest',
};

/**
 * Provides the application's root HTML layout, applies global font CSS variables and document-level links, and renders `children` inside the page body.
 *
 * @param children - Elements to render inside the document `<body>`
 * @returns The root HTML element tree for the application layout
 */
export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = normalizeWebguiLocale(await getLocale());

  return (
    <html
      lang={locale}
      className={`${jetBrainsMono.variable} ${jetBrainsMono.className} dark h-full antialiased`}
    >
      <body className='min-h-full flex flex-col'>
        <ControlRoomIntlProvider initialLocale={locale}>
          {children}
        </ControlRoomIntlProvider>
      </body>
    </html>
  );
}
