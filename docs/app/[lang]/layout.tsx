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
