import { RouterProvider } from "react-router-dom";
import { appRouter } from "./routes.jsx";
import { LoadingBlock } from "../../shared/ui/StateBlocks.jsx";

export function AppRouter() {
  return (
    <RouterProvider
      router={appRouter}
      fallbackElement={
        <div className="mx-auto flex min-h-screen w-full max-w-3xl items-center px-4 py-8">
          <LoadingBlock label="Loading route..." />
        </div>
      }
    />
  );
}
