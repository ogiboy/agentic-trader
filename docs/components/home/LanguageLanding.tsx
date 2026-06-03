import { Badge } from '@/components/ui/primitives/Badge';
import { Button } from '@/components/ui/primitives/Button';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/primitives/Card';
import { docLanguages, languageLabels } from '@/lib/i18n/config';
import { withLanguagePrefix } from '@/lib/i18n/routing';
import Link from 'next/link';

import { languageCardCopy, languageLandingCopy } from './content/language-landing-copy';

type LanguageLandingProps = {
  variant: 'root' | 'docs';
};

/**
 * Renders the language selection landing UI for the given page variant.
 *
 * @param variant - 'root' to use top-level language choice content, 'docs' to use documentation-routing content.
 * @returns The landing page JSX containing header badges and a card for each supported documentation language.
 */
export function LanguageLanding({ variant }: Readonly<LanguageLandingProps>) {
  const landingCopy = languageLandingCopy[variant];

  return (
    <main className='mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-6 py-12 sm:px-8'>
      <div className='docs-home-panel p-8 sm:p-10'>
        <div className='flex flex-wrap items-center gap-3'>
          <Badge variant='secondary'>{landingCopy.badge}</Badge>
          <Badge variant='outline'>EN / TR</Badge>
          <Badge variant='outline'>Fumadocs</Badge>
        </div>
        <div className='mt-6 flex max-w-3xl flex-col gap-4'>
          <h1 className='font-heading text-4xl font-semibold tracking-tight sm:text-5xl'>
            {landingCopy.title}
          </h1>
          <p className='max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg'>
            {landingCopy.description}
          </p>
        </div>
      </div>

      <section className='grid gap-5 md:grid-cols-2'>
        {docLanguages.map((lang) => {
          const cardCopy = languageCardCopy[lang];
          const Icon = cardCopy.icon;

          return (
            <Card key={lang} className='docs-home-panel'>
              <CardHeader>
                <CardTitle className='flex items-center gap-2 text-xl'>
                  <Icon data-icon='inline-start' />
                  {languageLabels[lang]}
                </CardTitle>
              </CardHeader>
              <CardContent className='flex flex-col gap-4'>
                <p className='text-sm text-muted-foreground'>
                  {cardCopy.description}
                </p>
                <div className='flex flex-wrap gap-3'>
                  <Button asChild>
                    <Link href={withLanguagePrefix(lang, '/docs')}>
                      {cardCopy.docsAction}
                    </Link>
                  </Button>
                  <Button asChild variant='outline'>
                    <Link href={withLanguagePrefix(lang, '/')}>
                      {cardCopy.homeAction}
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </section>
    </main>
  );
}
