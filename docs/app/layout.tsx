import type { ReactNode } from 'react';
import localFont from 'next/font/local';
import './globals.css';
export { docsMetadata as metadata } from '@/lib/site-metadata';

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

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${jetBrainsMono.variable} ${jetBrainsMono.className} flex min-h-screen flex-col bg-background text-foreground antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
