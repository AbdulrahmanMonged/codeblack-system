import { Button, Card, Chip } from "@heroui/react";
import { ArrowRight, Sparkles } from "lucide-react";

export function FeaturePlaceholder({
  title,
  description,
  badge,
  endpointHint,
  ctaLabel = "Implementation Phase",
}) {
  return (
    <Card className="cb-feature-card border border-white/15 bg-black/45 shadow-2xl backdrop-blur-xl">
      <Card.Header className="flex flex-col items-start gap-4 p-6">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-amber-300" />
          <Chip color="warning" variant="flat" size="sm">
            {badge || "Phase F0"}
          </Chip>
        </div>
        <div className="space-y-2">
          <Card.Title className="cb-feature-title text-3xl leading-none md:text-4xl">
            {title}
          </Card.Title>
          <Card.Description className="text-sm text-white/80 md:text-base">
            {description}
          </Card.Description>
        </div>
      </Card.Header>
      <Card.Content className="space-y-4 px-6 pb-6">
        {endpointHint ? (
          <div className="rounded-xl border border-amber-300/25 bg-amber-300/10 px-4 py-3 text-xs text-amber-100 md:text-sm">
            API target: <code>{endpointHint}</code>
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="solid" color="warning" endContent={<ArrowRight size={14} />}>
            {ctaLabel}
          </Button>
          <Button variant="ghost">UI Shell Ready</Button>
        </div>
      </Card.Content>
    </Card>
  );
}
