import { Button, Chip, Spinner } from "@heroui/react";
import { Bell, LogOut, Menu, ShieldCheck, UserCircle2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import useSWR from "swr";
import { useState } from "react";
import { toast } from "../ui/toast.jsx";
import { useAppDispatch, useAppSelector } from "../../app/store/hooks.js";
import {
  clearSession,
  selectCurrentUser,
  selectIsOwner,
  selectPermissions,
} from "../../app/store/slices/sessionSlice.js";
import {
  selectForceReducedMotion,
  setForceReducedMotion,
  toggleSidebar,
} from "../../app/store/slices/uiSlice.js";
import { hasAnyPermissionSet } from "../../core/permissions/guards.js";
import { logoutSession } from "../../features/auth/api/auth-api.js";
import { getNotificationsUnreadCount } from "../../features/notifications/api/notifications-api.js";

export function AppHeader() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const currentUser = useAppSelector(selectCurrentUser);
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);
  const forceReducedMotion = useAppSelector(selectForceReducedMotion);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const hasStaffView = hasAnyPermissionSet(
    [
      "applications.review",
      "orders.review",
      "audit.read",
      "discord_role_permissions.read",
      "config_registry.read",
      "bot.read_status",
    ],
    permissions,
    isOwner,
  );
  const canReadNotifications = hasAnyPermissionSet(["notifications.read"], permissions, isOwner);

  const { data: unreadData } = useSWR(
    canReadNotifications ? ["header-notifications-unread"] : null,
    () => getNotificationsUnreadCount(),
    { refreshInterval: 30000 },
  );

  async function handleLogout() {
    if (isLoggingOut) {
      return;
    }
    setIsLoggingOut(true);
    try {
      await logoutSession();
    } catch {
      // Session might already be expired; continue with local cleanup.
    } finally {
      dispatch(clearSession());
      toast.success("Logged out");
      navigate("/", { replace: true });
      setIsLoggingOut(false);
    }
  }

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-black/45 px-3 py-3 backdrop-blur-xl md:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Button
            isIconOnly
            variant="ghost"
            className="md:hidden"
            aria-label="Toggle sidebar"
            onPress={() => dispatch(toggleSidebar())}
          >
            <Menu size={16} />
          </Button>
          <div>
            <p className="cb-overline text-[11px] text-white/65">CodeBlack Control</p>
            <h1 className="cb-title text-xl">Operations Center</h1>
          </div>
        </div>

        <div className="ml-auto flex items-center gap-2 md:gap-3">
          <Chip variant="flat" color="warning" className="hidden md:inline-flex">
            Live Sync
          </Chip>
          <Button
            variant="ghost"
            className="hidden lg:inline-flex"
            onPress={() => dispatch(setForceReducedMotion(!forceReducedMotion))}
          >
            {forceReducedMotion ? "Motion Off" : "Motion On"}
          </Button>
          <Button
            isIconOnly
            variant="ghost"
            aria-label="Notifications"
            onPress={() => navigate("/notifications")}
          >
            <span className="relative inline-flex items-center justify-center">
              <Bell size={16} />
              {canReadNotifications && Number(unreadData?.unread_count || 0) > 0 ? (
                <span className="absolute -right-2.5 -top-2 rounded-full bg-amber-300 px-1.5 py-0.5 text-[10px] font-semibold text-black">
                  {unreadData.unread_count > 99 ? "99+" : unreadData.unread_count}
                </span>
              ) : null}
            </span>
          </Button>
          <Button
            variant="ghost"
            className="hidden sm:inline-flex"
            isDisabled={!hasStaffView}
            startContent={<ShieldCheck size={16} />}
          >
            Staff View
          </Button>
          <Button
            variant="solid"
            color="warning"
            aria-label="Profile"
            startContent={<UserCircle2 size={16} />}
            className="hidden sm:inline-flex"
          >
            {currentUser?.username || "Account"}
          </Button>
          <Button isIconOnly variant="solid" color="warning" aria-label="Profile" className="sm:hidden">
            <UserCircle2 size={16} />
          </Button>
          <Button
            isIconOnly
            variant="ghost"
            aria-label="Logout"
            isDisabled={isLoggingOut}
            isPending={isLoggingOut}
            onPress={handleLogout}
          >
            {isLoggingOut ? <Spinner color="current" size="sm" /> : <LogOut size={15} />}
          </Button>
        </div>
      </div>
    </header>
  );
}
