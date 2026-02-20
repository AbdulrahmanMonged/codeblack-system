import { useParams } from "react-router-dom";
import { FeaturePlaceholder } from "../../shared/ui/FeaturePlaceholder.jsx";

export function StaticFeaturePage({
  title,
  description,
  badge,
  endpointHint,
  ctaLabel,
}) {
  return (
    <FeaturePlaceholder
      title={title}
      description={description}
      badge={badge}
      endpointHint={endpointHint}
      ctaLabel={ctaLabel}
    />
  );
}

export function ParamFeaturePage({ title, description, endpointHintBuilder }) {
  const params = useParams();

  return (
    <FeaturePlaceholder
      title={title}
      description={description}
      badge="Dynamic Route"
      endpointHint={endpointHintBuilder(params)}
    />
  );
}
