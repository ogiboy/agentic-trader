import type { DocLanguage } from "@/lib/i18n/config";
import { getLayoutCopy } from "@/lib/navigation/nav-copy";

type DocsSidebarBannerProps = {
  locale: DocLanguage;
};

export function DocsSidebarBanner({
  locale,
}: Readonly<DocsSidebarBannerProps>) {
  const copy = getLayoutCopy(locale);

  return (
    <div className="rounded-xl border border-border/60 bg-card/60 p-3 text-sm text-muted-foreground">
      <p className="font-medium text-foreground">{copy.sidebarTitle}</p>
      <p className="mt-1">{copy.sidebarDescription}</p>
    </div>
  );
}
