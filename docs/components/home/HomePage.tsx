import { CurrentFocusPanel } from '@/components/home/CurrentFocusPanel';
import { EntryPointGrid } from '@/components/home/EntryPointGrid';
import { HomeHero } from '@/components/home/HomeHero';
import { RepoGuardrailAlert } from '@/components/home/RepoGuardrailAlert';
import { WorkflowTabs } from '@/components/home/WorkflowTabs';
import { getHomeContent } from '@/lib/home/content';
import type { DocLanguage } from '@/lib/i18n/config';

type HomePageProps = {
  locale: DocLanguage;
};

/**
 * Render the documentation home page for a given locale.
 *
 * Renders the full home page layout — hero, current focus panel, guardrail alert, entry points, and workflow tabs — using localized content for the supplied documentation language.
 *
 * @param locale - The documentation language/locale to render content for
 * @returns The JSX element for the localized documentation home page
 */
export function HomePage({ locale }: Readonly<HomePageProps>) {
  const content = getHomeContent(locale);

  return (
    <main className='mx-auto flex w-full max-w-7xl flex-1 flex-col gap-10 px-6 py-10 sm:px-8'>
      <section className='docs-home-grid items-start'>
        <HomeHero locale={locale} content={content} />
        <CurrentFocusPanel focus={content.currentFocus} />
      </section>
      <RepoGuardrailAlert locale={locale} text={content.guardrail} />
      <EntryPointGrid locale={locale} entryPoints={content.entryPoints} />
      <WorkflowTabs note={content.workflowNote} tracks={content.workflowTracks} />
    </main>
  );
}
