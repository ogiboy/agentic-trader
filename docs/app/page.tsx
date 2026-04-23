import Link from "next/link";
import {
  ArrowRight,
  Bot,
  ChartCandlestick,
  FileSearch,
  LayoutPanelTop,
  ShieldCheck,
  TerminalSquare,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const entryPoints = [
  {
    href: "/docs/getting-started",
    title: "Get Started",
    description:
      "Install the repo, run doctor, validate model readiness, and open the main operator surfaces.",
    badge: "Setup",
  },
  {
    href: "/docs/project-state",
    title: "Project State",
    description:
      "See what is already true, what is actively hardening, and which V1 constraints should not drift.",
    badge: "Status",
  },
  {
    href: "/docs/architecture",
    title: "Architecture",
    description:
      "See the staged specialist graph, package boundaries, and how runtime truth moves through the system.",
    badge: "System map",
  },
  {
    href: "/docs/bootstrap-and-onboarding",
    title: "Bootstrap And Onboarding",
    description:
      "Track the cross-platform setup path, provider-aware install plan, and app-managed Ollama direction.",
    badge: "Onboarding",
  },
  {
    href: "/docs/runtime",
    title: "Runtime Surfaces",
    description:
      "Understand CLI, Ink, Rich, observer API, and the thin Web GUI shell without inventing a second runtime.",
    badge: "Operators",
  },
  {
    href: "/docs/frontend-system",
    title: "Frontend System",
    description:
      "Keep `docs` and `webgui` aligned on the shared shadcn preset, JetBrains Mono typography, and incremental migration rules.",
    badge: "Frontend",
  },
  {
    href: "/docs/qa-and-debugging",
    title: "QA And Debugging",
    description:
      "Use smoke QA, runtime evidence, and operator-truth checks before treating a change as shippable.",
    badge: "Validation",
  },
];

const truthSources = [
  "README.md",
  "ROADMAP.md",
  "dev/code-map.md",
  ".ai/current-state.md",
  ".ai/tasks.md",
  ".ai/decisions.md",
];

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-10 px-6 py-10 sm:px-8">
      <section className="docs-home-grid items-start">
        <div className="docs-home-panel p-8 sm:p-10">
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="secondary">Developer Docs</Badge>
            <Badge variant="outline">Fumadocs + MDX</Badge>
            <Badge variant="outline">Local-first</Badge>
          </div>
          <div className="mt-6 flex max-w-3xl flex-col gap-5">
            <h1 className="font-heading text-4xl font-semibold tracking-tight sm:text-5xl">
              Build from the same runtime truth the operator sees.
            </h1>
            <p className="max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
              Agentic Trader is not a second-order chat demo. These docs are the
              developer surface for a strict, paper-first trading runtime with
              inspectable storage, explicit safety gates, and shared contracts
              across CLI, Ink, observer API, and Web GUI.
            </p>
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href="/docs">
                Read the docs
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href="/docs/getting-started">Open quick start</Link>
            </Button>
          </div>
          <Separator className="my-8" />
          <div className="grid gap-4 sm:grid-cols-3">
            <Card className="border-border/60 bg-background/40">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ChartCandlestick className="size-4" />
                  Runtime-first
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Model service, runtime state, broker state, and review surfaces
                should agree before we trust a cycle.
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-background/40">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <ShieldCheck className="size-4" />
                  Guardrailed
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                Paper execution, strict LLM gating, provider visibility, and no
                silent runtime fallbacks remain non-negotiable.
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-background/40">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-base">
                  <TerminalSquare className="size-4" />
                  Multi-surface
                </CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">
                CLI, Rich, Ink, observer API, and Web GUI all ride the same
                contracts instead of maintaining UI-only truth.
              </CardContent>
            </Card>
          </div>
        </div>

        <Card className="docs-home-panel sticky top-6">
          <CardHeader>
            <CardTitle>Current V1 focus</CardTitle>
            <CardDescription>
              The project is in hardening mode, not in “invent a parallel
              system” mode.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4 text-sm text-muted-foreground">
            <div className="flex items-start gap-3">
              <Bot className="mt-0.5 size-4 text-primary" />
              Optional app-managed Ollama supervision should extend the existing
              daemon and log surface.
            </div>
            <div className="flex items-start gap-3">
              <LayoutPanelTop className="mt-0.5 size-4 text-primary" />
              `webgui` stays a thin local shell while `docs` becomes the
              canonical dev-docs surface.
            </div>
            <div className="flex items-start gap-3">
              <FileSearch className="mt-0.5 size-4 text-primary" />
              Bootstrap, provider readiness, and QA evidence are all moving
              toward a more standardized onboarding path.
            </div>
          </CardContent>
        </Card>
      </section>

      <Alert className="docs-home-panel">
        <ShieldCheck className="size-4" />
        <AlertTitle>Repo guardrail</AlertTitle>
        <AlertDescription>
          The Web GUI and docs site are developer/operator surfaces. They do not
          own orchestration; Python runtime contracts remain the source of truth.
        </AlertDescription>
      </Alert>

      <section className="grid gap-5 xl:grid-cols-3">
        {entryPoints.map((item) => (
          <Card key={item.href} className="docs-home-panel">
            <CardHeader>
              <div className="flex items-center justify-between gap-3">
                <Badge variant="outline">{item.badge}</Badge>
              </div>
              <CardTitle>{item.title}</CardTitle>
              <CardDescription>{item.description}</CardDescription>
            </CardHeader>
            <CardFooter>
              <Button asChild variant="ghost">
                <Link href={item.href}>
                  Open section
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            </CardFooter>
          </Card>
        ))}
      </section>

      <section className="docs-home-panel p-6 sm:p-8">
        <Tabs className="flex flex-col gap-6" defaultValue="build">
          <TabsList className="w-full justify-start">
            <TabsTrigger value="build">Build</TabsTrigger>
            <TabsTrigger value="operate">Operate</TabsTrigger>
            <TabsTrigger value="inspect">Inspect</TabsTrigger>
          </TabsList>
          <TabsContent className="m-0" value="build">
            <div className="grid gap-4 lg:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Setup track</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Start with `README.md`, then validate the environment with
                  `doctor`, local model readiness, and the docs quick start.
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Architecture track</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Use `dev/code-map.md` plus the architecture docs to find the
                  smallest owning module before editing.
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Frontend track</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  `webgui` and `docs` share Next.js App Router, Tailwind v4, and
                  shadcn primitives, but they should not invent a shared package
                  prematurely.
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          <TabsContent className="m-0" value="operate">
            <div className="grid gap-4 lg:grid-cols-3">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Runtime mode</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Operation mode stays strict and paper-first; training mode is
                  for evaluation and replay, not hidden live-ish behavior.
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Model service</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Ollama reachability, model availability, and request/log tails
                  should be visible as operator truth, not inferred from silence.
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Operator surfaces</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  CLI, Ink, Rich, observer API, and Web GUI should all agree on
                  the same runtime and broker reality.
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          <TabsContent className="m-0" value="inspect">
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Source-of-truth files</CardTitle>
                  <CardDescription>
                    These are the first repo notes worth checking before a large
                    change.
                  </CardDescription>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  {truthSources.map((path) => (
                    <Badge key={path} variant="secondary">
                      {path}
                    </Badge>
                  ))}
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Validation mindset</CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Pair focused tests with smoke QA, JSON/runtime cross-checks,
                  and Computer Use or tmux evidence when an operator-facing
                  change affects layout or trust.
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </section>
    </main>
  );
}
