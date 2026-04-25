import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DocPageShell } from "@/components/docs/doc-page-shell";
import { getDocPage } from "@/lib/content/get-doc-page";
import { getDocLanguage } from "@/lib/i18n/routing";
import { source } from "@/lib/source";

type PageProps = {
  params: Promise<{ lang: string; slug?: string[] }>;
};

export default async function Page({ params }: Readonly<PageProps>) {
  const { lang: rawLang, slug = [] } = await params;
  const lang = getDocLanguage(rawLang);
  const page = getDocPage(slug, lang);

  if (!page) notFound();

  return <DocPageShell locale={lang} page={page} slug={slug} />;
}

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const { lang: rawLang, slug = [] } = await params;
  const lang = getDocLanguage(rawLang);
  const page = getDocPage(slug, lang);

  if (!page) notFound();

  return {
    title: page.data.title,
    description: page.data.description,
  };
}

export function generateStaticParams() {
  return source.generateParams("slug", "lang");
}
