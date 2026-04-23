import { EntryPointGrid } from "@/components/home/entry-point-grid";
import { HomeHero } from "@/components/home/home-hero";
import { CurrentFocusPanel } from "@/components/home/current-focus-panel";
import { RepoGuardrailAlert } from "@/components/home/repo-guardrail-alert";
import { WorkflowTabs } from "@/components/home/workflow-tabs";
import type { DocLanguage } from "@/lib/i18n/config";
import { getHomeContent } from "@/lib/home/content";

type HomePageProps = {
  locale: DocLanguage;
};

export function HomePage({ locale }: Readonly<HomePageProps>) {
  const content = getHomeContent(locale);

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-10 px-6 py-10 sm:px-8">
      <section className="docs-home-grid items-start">
        <HomeHero locale={locale} content={content} />
        <CurrentFocusPanel locale={locale} items={content.currentFocusItems} />
      </section>
      <RepoGuardrailAlert locale={locale} text={content.guardrail} />
      <EntryPointGrid locale={locale} entryPoints={content.entryPoints} />
      <WorkflowTabs locale={locale} tracks={content.workflowTracks} />
    </main>
  );
}
