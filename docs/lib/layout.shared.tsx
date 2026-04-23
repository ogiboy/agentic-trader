import { Blocks, ChartCandlestick, FileText, LayoutPanelTop, Rocket } from "lucide-react";
import type { BaseLayoutProps } from "fumadocs-ui/layouts/shared";

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      title: (
        <span className="inline-flex items-center gap-2 font-medium">
          <ChartCandlestick className="size-4" />
          Agentic Trader Docs
        </span>
      ),
      url: "/",
    },
    links: [
      {
        text: "Docs",
        url: "/docs",
        active: "nested-url",
        icon: <Blocks className="size-4" />,
      },
      {
        text: "Get Started",
        url: "/docs/getting-started",
        active: "nested-url",
        icon: <Rocket className="size-4" />,
      },
      {
        text: "Architecture",
        url: "/docs/architecture",
        active: "nested-url",
        icon: <FileText className="size-4" />,
      },
      {
        text: "Frontend",
        url: "/docs/frontend-system",
        active: "nested-url",
        icon: <LayoutPanelTop className="size-4" />,
      },
    ],
    githubUrl: "https://github.com/ogiboy/agentic-trader",
  };
}
