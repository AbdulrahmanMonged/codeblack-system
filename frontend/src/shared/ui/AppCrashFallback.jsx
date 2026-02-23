import { Button, Card } from "@heroui/react";
import { AlertTriangle, RefreshCcw } from "lucide-react";

export function AppCrashFallback({ error, resetErrorBoundary }) {
  return (
    <div className="mx-auto flex min-h-screen w-full max-w-3xl items-center px-4 py-10">
      <Card className="w-full border border-rose-300/25 bg-rose-300/10 p-6 shadow-2xl backdrop-blur-xl">
        <Card.Header className="flex items-start gap-3 p-0">
          <div className="rounded-lg border border-rose-200/30 bg-rose-300/20 p-2">
            <AlertTriangle size={17} className="text-rose-100" />
          </div>
          <div>
            <Card.Title className="cb-feature-title text-3xl text-rose-100">
              Application Error
            </Card.Title>
            <Card.Description className="mt-1 text-rose-100/85">
              A runtime error interrupted the current view. You can retry rendering.
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="space-y-4 px-0 pb-0 pt-4">
          {error?.message ? (
            <pre className="max-h-56 overflow-auto rounded-xl border border-rose-200/20 bg-black/30 p-3 text-xs text-rose-100/90">
              {error.message}
            </pre>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <Button
              color="warning"
              startContent={<RefreshCcw size={14} />}
              onPress={resetErrorBoundary}
            >
              Retry
            </Button>
            <Button variant="ghost" onPress={() => window.location.reload()}>
              Reload App
            </Button>
          </div>
        </Card.Content>
      </Card>
    </div>
  );
}
