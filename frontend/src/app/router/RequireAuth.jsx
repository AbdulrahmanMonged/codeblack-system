import { Spinner } from "@heroui/react";
import { Navigate } from "react-router-dom";
import { isAuthenticatedSession } from "../../core/auth/session.js";
import { useAppSelector } from "../store/hooks.js";
import { selectSessionStatus } from "../store/slices/sessionSlice.js";

export function RequireAuth({ children }) {
  const status = useAppSelector(selectSessionStatus);

  if (status === "unknown" || status === "hydrating") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="rounded-2xl border border-white/15 bg-black/50 px-8 py-6 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <Spinner size="sm" />
            <p className="text-sm text-white/80">Verifying session...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticatedSession(status)) {
    return <Navigate replace to="/" />;
  }

  return children;
}
