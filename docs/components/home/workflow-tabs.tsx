import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { DocLanguage } from "@/lib/i18n/config";
import type { WorkflowTrack } from "@/lib/home/content/types";

type WorkflowTabsProps = {
  locale: DocLanguage;
  tracks: WorkflowTrack[];
};

export function WorkflowTabs({
  locale,
  tracks,
}: Readonly<WorkflowTabsProps>) {
  return (
    <section className="docs-home-panel p-6 sm:p-8">
      <Tabs className="flex flex-col gap-6" defaultValue={tracks[0]?.id}>
        <TabsList className="w-full justify-start">
          {tracks.map((track) => (
            <TabsTrigger key={track.id} value={track.id}>
              {track.label}
            </TabsTrigger>
          ))}
        </TabsList>
        {tracks.map((track) => (
          <TabsContent key={track.id} className="m-0" value={track.id}>
            <div className="grid gap-4 lg:grid-cols-3">
              {track.cards.map((card) => (
                <Card key={card.title}>
                  <CardHeader>
                    <CardTitle className="text-base">{card.title}</CardTitle>
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {card.body}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
        ))}
      </Tabs>
      <p className="mt-5 text-sm text-muted-foreground">
        {locale === "en"
          ? "The docs should stay close to the runtime truth, not become a second architecture."
          : "Dokümanlar runtime gerçeğine yakın durmalı; ikinci bir mimari anlatısı olmamalı."}
      </p>
    </section>
  );
}
