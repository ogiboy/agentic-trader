import { Bot, FileSearch, LayoutPanelTop } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { DocLanguage } from "@/lib/i18n/config";

type CurrentFocusItem = {
  icon: "bot" | "layout" | "inspect";
  text: string;
};

type CurrentFocusPanelProps = {
  locale: DocLanguage;
  items: CurrentFocusItem[];
};

const icons = {
  bot: Bot,
  layout: LayoutPanelTop,
  inspect: FileSearch,
} as const;

export function CurrentFocusPanel({
  locale,
  items,
}: Readonly<CurrentFocusPanelProps>) {
  return (
    <Card className="docs-home-panel sticky top-6">
      <CardHeader>
        <CardTitle>
          {locale === "en" ? "Current V1 focus" : "Güncel V1 odağı"}
        </CardTitle>
        <CardDescription>
          {locale === "en"
            ? "The project is in hardening mode, not in “invent a parallel system” mode."
            : "Proje şu anda sertleştirme aşamasında; paralel bir sistem icat etme aşamasında değil."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 text-sm text-muted-foreground">
        {items.map((item) => {
          const Icon = icons[item.icon];

          return (
            <div key={item.text} className="flex items-start gap-3">
              <Icon className="mt-0.5 size-4 text-primary" />
              {item.text}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
