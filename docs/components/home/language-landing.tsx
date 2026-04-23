import Link from "next/link";
import { Globe2, Languages } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { docLanguages, languageLabels } from "@/lib/i18n/config";
import { withLanguagePrefix } from "@/lib/i18n/routing";

type LanguageLandingProps = {
  variant: "root" | "docs";
};

const copy = {
  root: {
    badge: "Documentation",
    title: "Choose your documentation language",
    description:
      "Agentic Trader docs now ship with English and Turkish entrypoints. Pick a language first, then continue into the same Fumadocs surface.",
  },
  docs: {
    badge: "Docs routing",
    title: "Docs now live under locale-aware routes",
    description:
      "Choose English or Turkish to open the full documentation tree. This keeps content, search, and navigation aligned for each language.",
  },
} as const;

export function LanguageLanding({
  variant,
}: Readonly<LanguageLandingProps>) {
  const landingCopy = copy[variant];

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-12 sm:px-8">
      <div className="docs-home-panel p-8 sm:p-10">
        <div className="flex flex-wrap items-center gap-3">
          <Badge variant="secondary">{landingCopy.badge}</Badge>
          <Badge variant="outline">EN / TR</Badge>
          <Badge variant="outline">Fumadocs</Badge>
        </div>
        <div className="mt-6 flex max-w-3xl flex-col gap-4">
          <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
            {landingCopy.title}
          </h1>
          <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            {landingCopy.description}
          </p>
        </div>
      </div>

      <section className="grid gap-5 md:grid-cols-2">
        {docLanguages.map((lang) => (
          <Card key={lang} className="docs-home-panel">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                {lang === "en" ? (
                  <Globe2 data-icon="inline-start" />
                ) : (
                  <Languages data-icon="inline-start" />
                )}
                {languageLabels[lang]}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <p className="text-sm text-muted-foreground">
                {lang === "en"
                  ? "Open the full documentation tree, landing page, and localized feedback messaging in English."
                  : "Tüm belge ağacını, başlangıç sayfasını ve yerelleştirilmiş geri bildirim akışını Türkçe olarak aç."}
              </p>
              <div className="flex flex-wrap gap-3">
                <Button asChild>
                  <Link href={withLanguagePrefix(lang, "/docs")}>
                    {lang === "en" ? "Open docs" : "Dokümanları aç"}
                  </Link>
                </Button>
                <Button asChild variant="outline">
                  <Link href={withLanguagePrefix(lang, "/")}>
                    {lang === "en" ? "Open home" : "Ana sayfayı aç"}
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </section>
    </main>
  );
}
