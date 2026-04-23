import type { ReactNode } from 'react';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { baseOptions } from '@/lib/layout.shared';
import { source } from '@/lib/source';

export default function Layout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <DocsLayout
      {...baseOptions()}
      tree={source.getPageTree()}
      sidebar={{
        banner: (
          <div className="rounded-xl border border-border/60 bg-card/60 p-3 text-sm text-muted-foreground">
            <p className="font-medium text-foreground">
              Local-first operator docs
            </p>
            <p className="mt-1">
              The docs follow the same runtime contracts that power CLI, Ink,
              and the Web GUI.
            </p>
          </div>
        ),
      }}
    >
      {children}
    </DocsLayout>
  );
}
