import { useAppSelector } from "../store/hooks.js";
import {
  selectIsOwner,
  selectPermissions,
  selectSessionStatus,
} from "../store/slices/sessionSlice.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../core/permissions/guards.js";
import { RequireAuth } from "./RequireAuth.jsx";
import { Navigate } from "react-router-dom";
import { useEffect } from "react";
import { toast } from "sonner";

export function RequirePermission({
  requiredPermissions = [],
  mode = "all",
  children,
  fallbackTitle,
  fallbackDescription,
}) {
  const sessionStatus = useAppSelector(selectSessionStatus);
  const isOwner = useAppSelector(selectIsOwner);
  const permissions = useAppSelector(selectPermissions);

  const allowed =
    mode === "any"
      ? hasAnyPermissionSet(requiredPermissions, permissions, isOwner)
      : hasPermissionSet(requiredPermissions, permissions, isOwner);

  useEffect(() => {
    if (sessionStatus === "authenticated" && !allowed) {
      toast.error(
        fallbackDescription || "You do not have permission to access this section.",
      );
    }
  }, [allowed, fallbackDescription, sessionStatus]);

  return (
    <RequireAuth>
      {sessionStatus === "authenticated" && allowed ? children : <Navigate replace to="/dashboard" />}
    </RequireAuth>
  );
}
