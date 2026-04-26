import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
} from "fumadocs-ui/layouts/docs/page";
import { Feedback } from "@/components/feedback/client";
import type { DocLanguage } from "@/lib/i18n/config";
import { getMDXComponents } from "@/mdx-components";
import type { source } from "@/lib/source";

type DocPage = ReturnType<typeof source.getPage>;

type DocPageShellProps = {
  locale: DocLanguage;
  page: NonNullable<DocPage>;
  slug: string[];
};

export function DocPageShell({
  locale,
  page,
  slug,
}: Readonly<DocPageShellProps>) {
  const MdxContent = page.data.body;

  return (
    <DocsPage toc={page.data.toc} full={page.data.full}>
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <DocsBody>
        <MdxContent components={getMDXComponents()} />
      </DocsBody>
      <Feedback
        key={`${locale}:${slug.join("/") || "index"}`}
        locale={locale}
        title={page.data.title}
      />
    </DocsPage>
  );
}
