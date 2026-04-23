import type { Metadata } from "next";
import { HomePage } from "@/components/home/home-page";
import {
  docLanguages,
  getDocLanguage,
  getHomeMetadata,
} from "@/lib/i18n/config";

type LocalePageProps = {
  params: Promise<{ lang: string }>;
};

export default async function Page({ params }: Readonly<LocalePageProps>) {
  const lang = getDocLanguage((await params).lang);

  return <HomePage locale={lang} />;
}

export async function generateMetadata({
  params,
}: LocalePageProps): Promise<Metadata> {
  const lang = getDocLanguage((await params).lang);
  return getHomeMetadata(lang);
}

export function generateStaticParams() {
  return docLanguages.map((lang) => ({ lang }));
}
