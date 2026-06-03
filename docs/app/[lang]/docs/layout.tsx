import { DocsSidebarBanner } from '@/components/layout/DocsSidebarBanner';
import { getDocLanguage } from '@/lib/i18n/routing';
import { baseOptions } from '@/lib/layout.shared';
import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import type { ReactNode } from 'react';

type DocsLayoutProps = {
  children: ReactNode;
  params: Promise<{ lang: string }>;
};

export default async function Layout({
  children,
  params,
}: Readonly<DocsLayoutProps>) {
  const lang = getDocLanguage((await params).lang);

  return (
    <DocsLayout
      {...baseOptions(lang)}
      tree={source.getPageTree(lang)}
      sidebar={{
        banner: <DocsSidebarBanner locale={lang} />,
      }}
    >
      {children}
    </DocsLayout>
  );
}
