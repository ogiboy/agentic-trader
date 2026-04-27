import type { ReactNode } from "react";
import { JetBrains_Mono } from "next/font/google";
import { RootProvider } from "fumadocs-ui/provider/next";
import { i18nUI } from "@/lib/layout.shared";
import { getDocLanguage } from "@/lib/i18n/routing";
import { basePath } from "@/lib/site-metadata";
import "../globals.css";
export { docsMetadata as metadata } from "@/lib/site-metadata";

const searchApi = `${basePath}/api/search`;
const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

type LocaleLayoutProps = {
  children: ReactNode;
  params: Promise<{ lang: string }>;
};

/**
 * Render the root HTML layout for a documentation locale.
 *
 * Resolves the route `lang` parameter to a documentation language, applies the JetBrains Mono font variable on the <html> element, and wraps `children` with the app-wide `RootProvider` configured with localized UI and a static search API.
 *
 * @param params - A promise resolving to route parameters containing `lang`, used to determine the document language
 * @returns The top-level HTML element for the locale-specific documentation page
 */
export default async function LocaleLayout({
  children,
  params,
}: Readonly<LocaleLayoutProps>) {
  const lang = getDocLanguage((await params).lang);

  return (
    <html
      lang={lang}
      suppressHydrationWarning
      className={jetbrainsMono.variable}
    >
      <body className="flex min-h-screen flex-col bg-background text-foreground antialiased">
        <RootProvider
          i18n={i18nUI.provider(lang)}
          search={{ options: { type: "static", api: searchApi } }}
        >
          {children}
        </RootProvider>
      </body>
    </html>
  );
}
