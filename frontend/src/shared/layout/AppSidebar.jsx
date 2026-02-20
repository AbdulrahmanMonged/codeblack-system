import { Button, Chip } from "@heroui/react";
import { cn } from "@heroui/react";
import { Shield, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import { APP_NAV_SECTIONS } from "../../app/router/navigation.js";
import { useAppDispatch, useAppSelector } from "../../app/store/hooks.js";
import {
  selectIsOwner,
  selectIsVerified,
  selectPermissions,
} from "../../app/store/slices/sessionSlice.js";
import { closeSidebar, selectSidebarOpen } from "../../app/store/slices/uiSlice.js";
import { hasAnyPermissionSet } from "../../core/permissions/guards.js";
import { useMotionPreference } from "../motion/useMotionPreference.js";

function SidebarLink({ to, label, isAllowed }) {
  const dispatch = useAppDispatch();
  if (!isAllowed) return null;

  return (
    <NavLink
      to={to}
      onClick={() => dispatch(closeSidebar())}
      className={({ isActive }) =>
        cn(
          "block rounded-xl border px-3 py-2 text-sm transition",
          isActive
            ? "border-amber-300/40 bg-amber-300/18 text-amber-100"
            : "border-transparent bg-white/5 text-white/85 hover:border-white/20 hover:bg-white/10",
        )
      }
    >
      {label}
    </NavLink>
  );
}

export function AppSidebar() {
  const dispatch = useAppDispatch();
  const isOpen = useAppSelector(selectSidebarOpen);
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);
  const isVerified = useAppSelector(selectIsVerified);
  const disableMotion = useMotionPreference();

  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden",
          disableMotion ? "duration-0" : "transition-opacity duration-200",
          isOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={() => dispatch(closeSidebar())}
      />
      <aside
        className={cn(
          "cb-sidebar fixed inset-y-0 left-0 z-40 h-screen w-[86vw] max-w-80 overflow-y-auto overflow-x-hidden border-r border-white/10 bg-black/60 p-4 pb-6 backdrop-blur-2xl md:static md:z-10 md:h-screen md:w-80 md:max-w-none md:translate-x-0 md:overflow-y-auto",
          disableMotion ? "duration-0" : "transition-transform duration-300",
          isOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <img
              src="/main/logo-on-hand.png"
              alt="CodeBlack logo"
              className="h-10 w-10 rounded-lg border border-amber-200/30 object-cover"
            />
            <div>
              <p className="cb-overline text-xs text-white/70">CodeBlack</p>
              <p className="cb-title text-lg">Dashboard</p>
            </div>
          </div>
          <Button
            isIconOnly
            variant="ghost"
            className="md:hidden"
            aria-label="Close sidebar"
            onPress={() => dispatch(closeSidebar())}
          >
            <X size={15} />
          </Button>
        </div>

        <div className="space-y-6 pt-6">
          {!isVerified ? (
            <section>
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-white/55">
                Account
              </p>
              <div className="space-y-2">
                <SidebarLink to="/verify-account" label="Verify Account" isAllowed />
              </div>
            </section>
          ) : null}
          {APP_NAV_SECTIONS.map((section) => (
            <section key={section.title}>
              <p className="mb-2 text-xs uppercase tracking-[0.2em] text-white/55">
                {section.title}
              </p>
              <div className="space-y-2">
                {section.items
                  .filter((item) =>
                    hasAnyPermissionSet(item.requiredAny, permissions, isOwner),
                  )
                  .map((item) => (
                  <SidebarLink
                    key={item.to}
                    to={item.to}
                    label={item.label}
                    isAllowed
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

        <div className="mt-8 rounded-xl border border-white/15 bg-black/45 p-4">
          <Chip color="warning" variant="flat" size="sm">
            Permissions active
          </Chip>
          <p className="mt-2 text-xs text-white/70">
            Final access rules will be loaded from the backend role matrix.
          </p>
          <div className="mt-3 inline-flex items-center gap-2 text-xs text-amber-100">
            <Shield size={13} />
            JWT cookie session mode
          </div>
        </div>
      </aside>
    </>
  );
}
