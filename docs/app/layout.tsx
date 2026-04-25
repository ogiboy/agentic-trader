import type { Metadata } from 'next';
import { JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { defaultLanguage } from '@/lib/i18n/config';

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
});

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? '';
const assetPath = (path: `/${string}`) => `${basePath}${path}`;

export const metadata: Metadata = {
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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang={defaultLanguage}
      suppressHydrationWarning
      className={jetbrainsMono.variable}
    >
      <body className="flex min-h-screen flex-col bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
