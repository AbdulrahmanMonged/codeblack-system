import { Button, Disclosure } from "@heroui/react";
import { useEffect, useMemo } from "react";
import { useLocation } from "react-router-dom";
import { useAppDispatch } from "../../app/store/hooks.js";
import { closeSidebar } from "../../app/store/slices/uiSlice.js";
import { AnimatedOutlet } from "../motion/AnimatedOutlet.jsx";
import { AppSidebar } from "./AppSidebar.jsx";
import { GlobalFooter } from "./GlobalFooter.jsx";
import { GlobalNavbar } from "./GlobalNavbar.jsx";
import { DashboardBreadcrumbs } from "./DashboardBreadcrumbs.jsx";

function toTitleCase(value) {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function resolveWorkspaceLabel(pathname) {
  const path = String(pathname || "");

  if (path === "/dashboard") return "Dashboard";
  if (path.startsWith("/admin/review-queue")) return "Review Queue";
  if (path.startsWith("/admin/audit")) return "Audit Timeline";
  if (path.startsWith("/permissions/role-matrix")) return "Role Matrix";
  if (path.startsWith("/config/registry")) return "Config Registry";
  if (path.startsWith("/bot/control")) return "Bot Control";
  if (path.startsWith("/verify-account")) return "Verify Account";

  const segments = path.split("/").filter(Boolean);
  if (!segments.length) {
    return "Workspace";
  }

  const lastSegment = segments[segments.length - 1];
  if (lastSegment && !/^[A-Za-z]{2,}-\d+$/i.test(lastSegment) && !/^\d+$/.test(lastSegment)) {
    return toTitleCase(lastSegment);
  }

  return toTitleCase(segments[0]);
}

export function AppShell() {
  const dispatch = useAppDispatch();
  const location = useLocation();

  const workspaceLabel = useMemo(
    () => resolveWorkspaceLabel(location.pathname),
    [location.pathname],
  );

  useEffect(() => {
    dispatch(closeSidebar());
  }, [dispatch, location.pathname]);

  return (
    <div className="flex h-screen w-full">
      <AppSidebar />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col md:ml-0">
        <div className="px-3 pt-3 md:px-6 md:pt-4">
          <GlobalNavbar embedded />
        </div>
        <main className="flex-1 overflow-y-auto px-3 py-4 md:px-6 md:py-6">
          <div className="mb-4">
            <DashboardBreadcrumbs />
          </div>

          <Disclosure defaultExpanded>
            <Disclosure.Heading>
              <Button className="w-full justify-between" slot="trigger" variant="secondary">
                {workspaceLabel} Workspace
                <Disclosure.Indicator />
              </Button>
            </Disclosure.Heading>
            <Disclosure.Content>
              <Disclosure.Body className="mt-3 rounded-2xl border border-white/10 bg-black/30 p-3">
                <AnimatedOutlet />
              </Disclosure.Body>
            </Disclosure.Content>
          </Disclosure>
        </main>
        <div className="px-3 pb-3 md:px-6 md:pb-4">
          <GlobalFooter embedded />
        </div>
      </div>
    </div>
  );
}
