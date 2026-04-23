import Link from "next/link";
import { ChartCandlestick, ShieldCheck, TerminalSquare } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { DocLanguage } from "@/lib/i18n/config";
import type { HomeContent } from "@/lib/home/content/types";
import { withLanguagePrefix } from "@/lib/i18n/routing";

type HomeHeroProps = {
  locale: DocLanguage;
  content: HomeContent;
};

export function HomeHero({ locale, content }: Readonly<HomeHeroProps>) {
  return (
    <div className="docs-home-panel p-8 sm:p-10">
      <div className="flex flex-wrap items-center gap-3">
        {content.badges.map((badge) => (
          <Badge key={badge.label} variant={badge.variant}>
            {badge.label}
          </Badge>
        ))}
      </div>
      <div className="mt-6 flex max-w-3xl flex-col gap-5">
        <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
          {content.heroTitle}
        </h1>
        <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
          {content.heroDescription}
        </p>
      </div>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button asChild size="lg">
          <Link href={withLanguagePrefix(locale, "/docs")}>
            {content.primaryAction}
          </Link>
        </Button>
        <Button asChild size="lg" variant="outline">
          <Link href={withLanguagePrefix(locale, content.secondaryAction.href)}>
            {content.secondaryAction.label}
          </Link>
        </Button>
      </div>
      <Separator className="my-8" />
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="border-border/60 bg-background/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ChartCandlestick className="size-4" />
              {content.trustCards.runtime.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {content.trustCards.runtime.body}
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-background/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ShieldCheck className="size-4" />
              {content.trustCards.safety.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {content.trustCards.safety.body}
          </CardContent>
        </Card>
        <Card className="border-border/60 bg-background/40">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TerminalSquare className="size-4" />
              {content.trustCards.surface.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {content.trustCards.surface.body}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
