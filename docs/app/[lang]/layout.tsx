import type { ReactNode } from "react";
import { RootProvider } from "fumadocs-ui/provider/next";
import { i18nUI } from "@/lib/layout.shared";
import { getDocLanguage } from "@/lib/i18n/routing";

type LocaleLayoutProps = {
  children: ReactNode;
  params: Promise<{ lang: string }>;
};

export default async function LocaleLayout({
  children,
  params,
}: Readonly<LocaleLayoutProps>) {
  const lang = getDocLanguage((await params).lang);

  return <RootProvider i18n={i18nUI.provider(lang)}>{children}</RootProvider>;
}
