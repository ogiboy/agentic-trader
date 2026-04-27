import { JetBrains_Mono } from 'next/font/google';
import '../globals.css';
export { docsMetadata as metadata } from '@/lib/site-metadata';

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-jetbrains-mono',
  subsets: ['latin'],
});

/**
 * Renders the root HTML layout for the landing page, applying the JetBrains Mono font variable and base layout classes.
 *
 * @param children - The content to be placed inside the page's <body>.
 * @returns The root HTML structure for the landing page containing the provided children.
 */
export default function LandingRootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={jetbrainsMono.variable}>
      <body className="flex min-h-screen flex-col bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
