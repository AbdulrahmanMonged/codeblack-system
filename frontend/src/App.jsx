
import { ErrorBoundary } from "react-error-boundary";
import { AppProviders } from "./app/providers/AppProviders.jsx";
import { AppRouter } from "./app/router/AppRouter.jsx";
import { AppCrashFallback } from "./shared/ui/AppCrashFallback.jsx";

export default function App() {
  return (
    <ErrorBoundary FallbackComponent={AppCrashFallback}>
      <AppProviders>
        <AppRouter />
      </AppProviders>
    </ErrorBoundary>
  );
}
