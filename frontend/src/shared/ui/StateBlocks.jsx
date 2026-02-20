import { Button, Card } from "@heroui/react";
import { AlertTriangle, Inbox, LoaderCircle, RefreshCcw } from "lucide-react";

export function LoadingBlock({ label = "Loading..." }) {
  return (
    <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
      <div className="flex items-center gap-3 text-sm text-white/75">
        <LoaderCircle size={16} className="animate-spin text-amber-200" />
        <span>{label}</span>
      </div>
    </Card>
  );
}

export function EmptyBlock({
  title = "No data",
  description = "There is nothing to show for this state.",
}) {
  return (
    <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
      <div className="flex items-start gap-3">
        <div className="rounded-lg border border-white/15 bg-white/5 p-2">
          <Inbox size={16} className="text-white/75" />
        </div>
        <div>
          <p className="text-sm font-semibold text-white">{title}</p>
          <p className="mt-1 text-sm text-white/65">{description}</p>
        </div>
      </div>
    </Card>
  );
}

export function ErrorBlock({
  title = "Something went wrong",
  description,
  onRetry,
  retryLabel = "Retry",
}) {
  return (
    <Card className="border border-rose-300/25 bg-rose-300/10 p-4 shadow-2xl backdrop-blur-xl">
      <div className="flex items-start gap-3">
        <div className="rounded-lg border border-rose-200/35 bg-rose-300/20 p-2">
          <AlertTriangle size={16} className="text-rose-100" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-rose-100">{title}</p>
          {description ? <p className="mt-1 text-sm text-rose-100/85">{description}</p> : null}
          {onRetry ? (
            <Button
              className="mt-3"
              size="sm"
              variant="flat"
              startContent={<RefreshCcw size={14} />}
              onPress={onRetry}
            >
              {retryLabel}
            </Button>
          ) : null}
        </div>
      </div>
    </Card>
  );
}
