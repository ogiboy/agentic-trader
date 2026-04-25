import type { Metadata } from 'next';
import { JetBrains_Mono } from 'next/font/google';
import { headers } from 'next/headers';
import './globals.css';
import { getDocLanguage } from '@/lib/i18n/routing';

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: {
    default: 'Agentic Trader Docs',
    template: '%s | Agentic Trader Docs',
  },
  description:
    'Developer documentation for the local-first Agentic Trader runtime, operator surfaces, and QA workflow.',

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

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const requestHeaders = await headers();
  const lang = getDocLanguage(requestHeaders.get('x-agentic-doc-lang') ?? undefined);

  return (
    <html lang={lang} suppressHydrationWarning className={jetbrainsMono.variable}>
      <body className="flex min-h-screen flex-col bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
