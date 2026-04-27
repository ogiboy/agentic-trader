import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import type { DocLanguage } from '@/lib/i18n/config';
import { withLanguagePrefix } from '@/lib/i18n/routing';
import type { HomeEntryPoint } from '@/lib/home/content/types';

type EntryPointGridProps = {
  locale: DocLanguage;
  entryPoints: HomeEntryPoint[];
};

const openSectionLabel: Record<DocLanguage, string> = {
  en: 'Open section',
  tr: 'Bölümü aç',
};

export function EntryPointGrid({
  locale,
  entryPoints,
}: Readonly<EntryPointGridProps>) {
  return (
    <section className="grid gap-5 xl:grid-cols-3">
      {entryPoints.map((item) => (
        <Card key={item.href} className="docs-home-panel">
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <Badge variant="outline">{item.badge}</Badge>
            </div>
            <CardTitle>{item.title}</CardTitle>
            <CardDescription>{item.description}</CardDescription>
          </CardHeader>
          <CardFooter>
            <Button asChild variant="ghost">
              <Link href={withLanguagePrefix(locale, item.href)}>
                {openSectionLabel[locale]}
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          </CardFooter>
        </Card>
      ))}
    </section>
  );
}
