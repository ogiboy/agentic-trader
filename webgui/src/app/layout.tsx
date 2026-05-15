import type { Metadata } from 'next';
import localFont from 'next/font/local';
import './globals.css';

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
  title: 'Agentic Trader Web GUI',
  description: 'Local-first command center for Agentic Trader',
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
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${jetBrainsMono.variable} ${jetBrainsMono.className} dark h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
