import { useEffect } from "react";
import { apiRequest } from "../../core/api/http-client.js";
import { FRONTEND_DEV_UNLOCK_ALL } from "../../core/config/env.js";
import { mapAuthUserToSessionPayload } from "../../features/auth/utils/session-mapper.js";
import { useAppDispatch } from "../store/hooks.js";
import {
  hydrationCompleted,
  hydrationFailed,
  hydrationStarted,
} from "../store/slices/sessionSlice.js";

const DEV_UNLOCK_SESSION_PAYLOAD = {
  user: {
    userId: "dev-unlock",
    discordUserId: "dev-unlock",
    username: "Dev Unlock Owner",
    avatarUrl: null,
    accountName: "dev-unlock",
    isVerified: true,
  },
  roleIds: [],
  permissions: [],
  isOwner: true,
  isVerified: true,
};

export function SessionBootstrap({ children }) {
  const dispatch = useAppDispatch();

  useEffect(() => {
    let cancelled = false;

    async function hydrateSession() {
      dispatch(hydrationStarted());

      if (FRONTEND_DEV_UNLOCK_ALL) {
        if (!cancelled) {
          dispatch(hydrationCompleted(DEV_UNLOCK_SESSION_PAYLOAD));
        }
        return;
      }

      const isAuthCallbackRoute =
        typeof window !== "undefined" && window.location.pathname === "/auth/callback";
      if (isAuthCallbackRoute) {
        return;
      }

      try {
        const user = await apiRequest("/auth/me", { method: "GET" });
        if (cancelled) {
          return;
        }
        dispatch(hydrationCompleted(mapAuthUserToSessionPayload(user)));
      } catch {
        if (!cancelled) {
          dispatch(hydrationFailed());
        }
      }
    }

    hydrateSession();
    return () => {
      cancelled = true;
    };
  }, [dispatch]);

  return children;
}
