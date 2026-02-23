import { Card } from "@heroui/react";
import { Lock } from "lucide-react";

export function ForbiddenState({
  title = "Insufficient Permissions",
  description = "You do not have the required permissions for this action.",
}) {
  return (
    <Card className="border border-rose-300/25 bg-rose-300/10 p-6 shadow-2xl backdrop-blur-xl">
      <Card.Header className="flex items-start gap-3 p-0">
        <div className="rounded-lg border border-rose-200/30 bg-rose-300/20 p-2">
          <Lock size={16} className="text-rose-100" />
        </div>
        <div>
          <Card.Title className="cb-feature-title text-2xl text-rose-100">{title}</Card.Title>
          <Card.Description className="mt-1 text-rose-100/80">{description}</Card.Description>
        </div>
      </Card.Header>
    </Card>
  );
}
