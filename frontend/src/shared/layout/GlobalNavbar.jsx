import { Avatar, Button, Card, Chip, Spinner } from "@heroui/react";
import { Bell, DoorOpen, LayoutDashboard, Menu, X } from "lucide-react";
import { Icon } from "@iconify/react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import useSWR from "swr";
import { useState } from "react";
import { toast } from "../ui/toast.jsx";
import { useAppDispatch, useAppSelector } from "../../app/store/hooks.js";
import {
  clearSession,
  selectCurrentUser,
  selectIsOwner,
  selectIsVerified,
  selectPermissions,
  selectSessionStatus,
} from "../../app/store/slices/sessionSlice.js";
import {
  selectSidebarOpen,
  toggleSidebar,
} from "../../app/store/slices/uiSlice.js";
import { hasAnyPermissionSet } from "../../core/permissions/guards.js";
import {
  createDiscordLogin,
  logoutSession,
} from "../../features/auth/api/auth-api.js";
import {
  deleteAllNotifications,
  getNotificationsUnreadCount,
  listNotifications,
  markAllNotificationsRead,
} from "../../features/notifications/api/notifications-api.js";
import { extractApiErrorMessage } from "../../core/api/error-utils.js";
import { toArray } from "../utils/collections.js";
import { resolveMediaUrl } from "../utils/media.js";

function NavItem({ to, label, active }) {
  return (
    <Link
      to={to}
      className={[
        "rounded-full px-3 py-1.5 text-sm transition",
        active
          ? "bg-amber-300/25 text-amber-100"
          : "text-white/80 hover:bg-white/10 hover:text-white",
      ].join(" ")}
    >
      {label}
    </Link>
  );
}

function toInitials(name) {
  const source = String(name || "").trim();
  if (!source) return "U";
  const parts = source.split(/\s+/).filter(Boolean);
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0] || ""}${parts[1][0] || ""}`.toUpperCase();
}

export function GlobalNavbar({ embedded = false }) {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useAppDispatch();
  const sessionStatus = useAppSelector(selectSessionStatus);
  const currentUser = useAppSelector(selectCurrentUser);
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);
  const isVerified = useAppSelector(selectIsVerified);
  const sidebarOpen = useAppSelector(selectSidebarOpen);
  const isAuthenticated = sessionStatus === "authenticated";
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [isSignInRedirecting, setIsSignInRedirecting] = useState(false);
  const isAuthCallbackRoute = location.pathname === "/auth/callback";
  const isDashboardActive = location.pathname === "/dashboard";
  const isVerifyActive = location.pathname === "/verify-account";
  const isProtectedDashboardRoute = (() => {
    const path = location.pathname;
    if (path === "/applications/new" || path === "/applications/eligibility") {
      return false;
    }
    return (
      path === "/dashboard" ||
      path === "/verify-account" ||
      path === "/notifications" ||
      path.startsWith("/applications") ||
      path.startsWith("/orders") ||
      path.startsWith("/roster") ||
      path.startsWith("/playerbase") ||
      path.startsWith("/blacklist") ||
      path.startsWith("/activities") ||
      path.startsWith("/vacations") ||
      path.startsWith("/posts") ||
      path.startsWith("/voting") ||
      path.startsWith("/admin") ||
      path.startsWith("/permissions") ||
      path.startsWith("/config") ||
      path.startsWith("/bot")
    );
  })();

  const canReadNotifications = hasAnyPermissionSet(["notifications.read"], permissions, isOwner);
  const { data: unreadData, mutate: refreshUnread } = useSWR(
    canReadNotifications && isAuthenticated ? ["navbar-notifications-unread"] : null,
    () => getNotificationsUnreadCount(),
  );
  const { data: unreadList, mutate: refreshUnreadList } = useSWR(
    canReadNotifications && isAuthenticated && notificationsOpen
      ? ["navbar-notifications-list"]
      : null,
    () => listNotifications({ unreadOnly: true, limit: 15, offset: 0 }),
  );

  async function handleLogout() {
    try {
      await logoutSession();
    } catch {
      // session may already be invalidated
    }
    dispatch(clearSession());
    toast.success("Signed out");
    navigate("/");
  }

  async function handleMarkAllRead() {
    try {
      await markAllNotificationsRead();
      await Promise.all([refreshUnread(), refreshUnreadList()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to mark notifications as read"));
    }
  }

  async function handleDeleteAll() {
    try {
      await deleteAllNotifications();
      await Promise.all([refreshUnread(), refreshUnreadList()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to delete notifications"));
    }
  }

  async function handleSignIn() {
    setIsSignInRedirecting(true);
    try {
      const nextUrl = `${location.pathname || "/"}${location.search || ""}${
        location.hash || ""
      }`;
      const payload = await createDiscordLogin({
        nextUrl: nextUrl === "/" ? "/dashboard" : nextUrl,
      });
      if (!payload?.authorize_url) {
        throw new Error("Missing Discord authorize URL");
      }
      window.location.assign(payload.authorize_url);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to start Discord sign-in"));
      setIsSignInRedirecting(false);
    }
  }

  return (
    <div
      className={
        embedded
          ? "relative z-20"
          : "pointer-events-none fixed inset-x-0 top-3 z-50 px-3 md:px-6"
      }
    >
      <div
        className={
          embedded
            ? "pointer-events-auto flex w-full items-center justify-between gap-3 rounded-2xl border border-white/20 bg-black/55 px-4 py-3 shadow-2xl backdrop-blur-xl"
            : "pointer-events-auto mx-auto flex max-w-7xl items-center justify-between gap-3 rounded-2xl border border-white/20 bg-black/55 px-4 py-3 shadow-2xl backdrop-blur-xl"
        }
      >
        <div className="flex items-center gap-3">
          {isAuthenticated && isProtectedDashboardRoute ? (
            <Button
              isIconOnly
              variant="ghost"
              className="md:hidden"
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
              onPress={() => dispatch(toggleSidebar())}
            >
              {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
            </Button>
          ) : null}
          <img
            src={resolveMediaUrl("/main-logo/codeblack-round-logo.png")}
            alt="CodeBlack logo"
            className="h-9 w-9 rounded-full border border-amber-200/40 object-cover transition hover:scale-105"
          />
          <div className="hidden sm:block">
            <p className="cb-title text-sm tracking-wide text-white transition hover:text-amber-100">
              Codeblack Operations Center
            </p>
          </div>
        </div>

        <div className="hidden items-center gap-1 md:flex">
          <NavItem
            to="/roster-public"
            label="Roster"
            active={location.pathname === "/roster-public"}
          />
          <NavItem to="/" label="Homepage" active={location.pathname === "/"} />
        </div>

        <div className="flex items-center gap-2">
          {isAuthenticated && canReadNotifications ? (
            <div className="relative">
              <Button
                isIconOnly
                variant="ghost"
                aria-label="Notifications"
                onPress={() => setNotificationsOpen((value) => !value)}
              >
                <span className="relative">
                  <Bell size={16} />
                  {Number(unreadData?.unread_count || 0) > 0 ? (
                    <span className="absolute -right-2 -top-2 rounded-full bg-amber-300 px-1.5 py-0.5 text-[10px] font-semibold text-black">
                      {unreadData.unread_count > 99 ? "99+" : unreadData.unread_count}
                    </span>
                  ) : null}
                </span>
              </Button>
              {notificationsOpen ? (
                <Card className="absolute right-0 top-11 z-20 w-[320px] border border-white/15 bg-black/80 p-3 shadow-2xl backdrop-blur-xl">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-sm font-semibold text-white">Unread notifications</p>
                    <Chip variant="flat">{unreadData?.unread_count || 0}</Chip>
                  </div>
                  <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                    {toArray(unreadList).map((item) => (
                      <div
                        key={item.public_id}
                        className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/85"
                      >
                        <p className="font-semibold text-white">{item.title}</p>
                        <p className="mt-1 line-clamp-2 text-white/70">{item.body}</p>
                      </div>
                    ))}
                    {!toArray(unreadList).length ? (
                      <p className="rounded-xl border border-white/10 bg-white/5 p-2 text-xs text-white/65">
                        No unread notifications.
                      </p>
                    ) : null}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" variant="flat" onPress={handleMarkAllRead}>
                      Mark all read
                    </Button>
                    <Button size="sm" variant="ghost" onPress={handleDeleteAll}>
                      Delete all
                    </Button>
                    <Button
                      size="sm"
                      color="warning"
                      onPress={() => {
                        setNotificationsOpen(false);
                        navigate("/notifications");
                      }}
                    >
                      Open center
                    </Button>
                  </div>
                </Card>
              ) : null}
            </div>
          ) : null}

          {isAuthenticated ? (
            <>
              {!isVerified ? (
                <Button
                  color="warning"
                  variant={isVerifyActive ? "flat" : "ghost"}
                  onPress={() => navigate("/verify-account")}
                >
                  Verify
                </Button>
              ) : null}
              <Button
                variant={isDashboardActive ? "flat" : "ghost"}
                className={isDashboardActive ? "border border-amber-300/35 bg-amber-300/15" : undefined}
                startContent={<LayoutDashboard size={14} />}
                onPress={() => navigate("/dashboard")}
              >
                Dashboard
              </Button>
              <div className="hidden items-center gap-2 rounded-full border border-white/15 bg-white/5 px-2 py-1 sm:flex">
                <Avatar size="sm">
                  <Avatar.Image
                    alt={currentUser?.username || "User"}
                    src={currentUser?.avatarUrl || undefined}
                  />
                  <Avatar.Fallback>
                    {toInitials(currentUser?.username || "User")}
                  </Avatar.Fallback>
                </Avatar>
                <span className="max-w-24 truncate text-sm text-white/85">
                  {currentUser?.username || "Account"}
                </span>
              </div>
              <Button
                isIconOnly
                variant="ghost"
                aria-label="Sign out"
                onPress={handleLogout}
              >
                <DoorOpen size={16} />
              </Button>
            </>
          ) : (
            <Button
              color="warning"
              isPending={isSignInRedirecting || isAuthCallbackRoute}
              isDisabled={isSignInRedirecting || isAuthCallbackRoute}
              onPress={handleSignIn}
            >
              {({ isPending }) => (
                <>
                  {isPending ? (
                    <Spinner color="current" size="sm" />
                  ) : (
                    <Icon icon="ri:discord-fill" width="16" height="16" />
                  )}
                  {isAuthCallbackRoute ? "Verifying..." : "Sign In"}
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
