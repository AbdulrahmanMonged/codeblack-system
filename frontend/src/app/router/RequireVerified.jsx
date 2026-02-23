import { useEffect } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { toast } from "../../shared/ui/toast.jsx";
import { useAppSelector } from "../store/hooks.js";
import {
  selectIsOwner,
  selectIsVerified,
  selectSessionStatus,
} from "../store/slices/sessionSlice.js";

export function RequireVerified({ children }) {
  const location = useLocation();
  const sessionStatus = useAppSelector(selectSessionStatus);
  const isOwner = useAppSelector(selectIsOwner);
  const isVerified = useAppSelector(selectIsVerified);

  const allowed = sessionStatus === "authenticated" && (isOwner || isVerified);

  useEffect(() => {
    if (!allowed && sessionStatus === "authenticated") {
      toast.warning("Account verification is required to access dashboard features.");
    }
  }, [allowed, sessionStatus]);

  if (!allowed) {
    return (
      <Navigate
        replace
        to="/verify-account"
        state={{ from: location.pathname }}
      />
    );
  }

  return children;
}
