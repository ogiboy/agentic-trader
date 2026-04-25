import type { DocLanguage } from "@/lib/i18n/config";

const layoutCopy = {
  en: {
    docs: "Docs",
    gettingStarted: "Get Started",
    architecture: "Architecture",
    frontend: "Frontend",
    sidebarTitle: "Local-first operator docs",
    sidebarDescription:
      "The docs follow the same runtime contracts that power CLI, Ink, and the Web GUI.",
  },
  tr: {
    docs: "Dokümanlar",
    gettingStarted: "Başlangıç",
    architecture: "Mimari",
    frontend: "Frontend",
    sidebarTitle: "Local-first operatör dokümanları",
    sidebarDescription:
      "Bu dokümanlar CLI, Ink ve Web GUI'nin kullandığı aynı runtime sözleşmelerini takip eder.",
  },
} as const;

export function getLayoutCopy(locale: DocLanguage) {
  return layoutCopy[locale];
}
