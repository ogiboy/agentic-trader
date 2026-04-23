import { ChartCandlestick } from "lucide-react";
import { defineI18nUI } from "fumadocs-ui/i18n";
import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";
import { i18n, languageLabels, type DocLanguage } from "@/lib/i18n/config";
import { withLanguagePrefix } from "@/lib/i18n/routing";

export const i18nUI = defineI18nUI(i18n, {
  en: {
    displayName: languageLabels.en,
  },
  tr: {
    displayName: languageLabels.tr,
    search: "Dokümanlarda ara",
  },
});

export function baseOptions(locale: DocLanguage): BaseLayoutProps {
  return {
    i18n,
    nav: {
      title: (
        <span className="inline-flex items-center gap-2 font-medium">
          <ChartCandlestick className="size-4" />
          Agentic Trader Docs
        </span>
      ),
      url: withLanguagePrefix(locale, "/"),
    },
    githubUrl: "https://github.com/ogiboy/agentic-trader",
  };
}
