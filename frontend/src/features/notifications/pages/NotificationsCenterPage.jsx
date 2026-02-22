import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import {
  Bell,
  CheckCheck,
  Megaphone,
  RefreshCw,
  Send,
  ShieldAlert,
} from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { FormInput, FormSelect, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../../shared/ui/StateBlocks.jsx";
import { toArray } from "../../../shared/utils/collections.js";
import {
  broadcastNotification,
  deleteAllNotifications,
  deleteNotification,
  getNotificationsUnreadCount,
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  sendTargetedNotification,
} from "../api/notifications-api.js";

function severityChipColor(severity) {
  const value = String(severity || "").toLowerCase();
  if (value === "success") return "success";
  if (value === "warning") return "warning";
  if (value === "critical") return "danger";
  return "default";
}

export function NotificationsCenterPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["notifications.read"], permissions, isOwner);
  const canBroadcast = hasPermissionSet(["notifications.broadcast"], permissions, isOwner);
  const canTargeted = hasPermissionSet(["notifications.send_targeted"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(
    ["notifications.read", "notifications.broadcast", "notifications.send_targeted"],
    permissions,
    isOwner,
  );

  const [unreadOnly, setUnreadOnly] = useState(false);
  const [selectedPublicId, setSelectedPublicId] = useState("");
  const [metadataRaw, setMetadataRaw] = useState("{}");

  const {
    data: notifications,
    error: notificationsError,
    isLoading: notificationsLoading,
    mutate: refreshNotifications,
  } = useSWR(
    canRead ? ["notifications-list", unreadOnly ? "unread" : "all"] : null,
    () => listNotifications({ unreadOnly, limit: 100, offset: 0 }),
  );

  const { data: unreadData, mutate: refreshUnread } = useSWR(
    canRead ? ["notifications-unread-count"] : null,
    () => getNotificationsUnreadCount(),
  );

  const notificationRows = useMemo(() => toArray(notifications), [notifications]);

  const selectedNotification = useMemo(
    () => notificationRows.find((item) => item.public_id === selectedPublicId) || null,
    [notificationRows, selectedPublicId],
  );

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Notifications Access Restricted"
        description="You need notifications permissions to use this page."
      />
    );
  }

  async function handleMarkRead(publicId) {
    try {
      await markNotificationRead(publicId);
      await Promise.all([refreshNotifications(), refreshUnread()]);
      toast.success("Notification marked as read");
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to mark notification as read"));
    }
  }

  async function handleMarkAllRead() {
    try {
      const result = await markAllNotificationsRead();
      await Promise.all([refreshNotifications(), refreshUnread()]);
      toast.success(`Marked ${result.updated_count || 0} notifications as read`);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to mark all notifications as read"));
    }
  }

  async function handleBroadcast(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const metadataValue = String(metadataRaw || "").trim();
    let parsedMetadata = null;
    if (metadataValue) {
      try {
        parsedMetadata = JSON.parse(metadataValue);
      } catch {
        toast.error("Metadata must be valid JSON");
        return;
      }
    }

    const payload = {
      event_type: String(form.get("eventType") || "").trim(),
      category: String(form.get("category") || "").trim(),
      severity: String(form.get("severity") || "info").trim(),
      title: String(form.get("title") || "").trim(),
      body: String(form.get("body") || "").trim(),
      entity_type: String(form.get("entityType") || "").trim() || null,
      entity_public_id: String(form.get("entityPublicId") || "").trim() || null,
      metadata_json: parsedMetadata,
    };
    if (!payload.event_type || !payload.category || !payload.title || !payload.body) {
      toast.error("Event type, category, title, and body are required");
      return;
    }
    try {
      await broadcastNotification(payload);
      toast.success("Broadcast sent");
      formElement?.reset?.();
      setMetadataRaw("{}");
      await Promise.all([refreshNotifications(), refreshUnread()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to broadcast notification"));
    }
  }

  async function handleTargetedSend(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const parseIds = (raw) =>
      String(raw || "")
        .split(",")
        .map((item) => Number(item.trim()))
        .filter((value) => Number.isFinite(value) && value > 0);

    const payload = {
      event_type: String(form.get("eventType") || "").trim(),
      category: String(form.get("category") || "").trim(),
      severity: String(form.get("severity") || "info").trim(),
      title: String(form.get("title") || "").trim(),
      body: String(form.get("body") || "").trim(),
      user_ids: parseIds(form.get("userIds")),
      role_ids: parseIds(form.get("roleIds")),
      entity_type: String(form.get("entityType") || "").trim() || null,
      entity_public_id: String(form.get("entityPublicId") || "").trim() || null,
      metadata_json: null,
    };
    if (!payload.event_type || !payload.category || !payload.title || !payload.body) {
      toast.error("Event type, category, title, and body are required");
      return;
    }
    if (!payload.user_ids.length && !payload.role_ids.length) {
      toast.error("Provide at least one user id or role id");
      return;
    }
    try {
      await sendTargetedNotification(payload);
      toast.success("Targeted notification sent");
      formElement?.reset?.();
      await Promise.all([refreshNotifications(), refreshUnread()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to send targeted notification"));
    }
  }

  async function handleDelete(publicId) {
    try {
      await deleteNotification(publicId);
      await Promise.all([refreshNotifications(), refreshUnread()]);
      if (selectedPublicId === publicId) {
        setSelectedPublicId("");
      }
      toast.success("Notification deleted");
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to delete notification"));
    }
  }

  async function handleDeleteAll() {
    try {
      const result = await deleteAllNotifications();
      await Promise.all([refreshNotifications(), refreshUnread()]);
      setSelectedPublicId("");
      toast.success(`Deleted ${result.deleted_count || 0} notifications`);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to delete all notifications"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Notifications Center
              </Chip>
              <Chip variant="flat" startContent={<Bell size={13} />}>
                Unread {unreadData?.unread_count || 0}
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Notifications</h2>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {canRead ? (
              <>
                <Button
                  variant="ghost"
                  startContent={<CheckCheck size={15} />}
                  onPress={handleMarkAllRead}
                >
                  Read All
                </Button>
                <Button variant="ghost" onPress={handleDeleteAll}>
                  Delete All
                </Button>
                <Button
                  variant="ghost"
                  startContent={<RefreshCw size={15} />}
                  onPress={() => Promise.all([refreshNotifications(), refreshUnread()])}
                >
                  Refresh
                </Button>
              </>
            ) : null}
          </div>
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-4">
          {canRead ? (
            <>
              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
                <label className="inline-flex items-center gap-2 text-sm text-white/80">
                  <FormInput
                    type="checkbox"
                    checked={unreadOnly}
                    onChange={(event) => setUnreadOnly(event.target.checked)}
                  />
                  Show unread only
                </label>
              </Card>

              <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
                <div className="mb-2 flex items-center justify-between px-2 py-1">
                  <p className="text-sm text-white/70">
                    Notifications:{" "}
                    <span className="font-semibold text-white">{notificationRows.length}</span>
                  </p>
                </div>
                <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
                  {notificationsLoading ? <LoadingBlock label="Loading notifications..." /> : null}
                  {notificationRows.map((item) => {
                    const active = item.public_id === selectedPublicId;
                    return (
                      <button
                        key={item.public_id}
                        type="button"
                        onClick={() => setSelectedPublicId(item.public_id)}
                        className={[
                          "w-full rounded-xl border p-3 text-left transition",
                          active
                            ? "border-amber-300/45 bg-amber-300/15"
                            : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                        ].join(" ")}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-white">{item.title}</p>
                          <div className="flex items-center gap-2">
                            <Chip size="sm" color={severityChipColor(item.severity)} variant="flat">
                              {item.severity}
                            </Chip>
                            <Chip size="sm" variant="flat">
                              {item.is_read ? "read" : "unread"}
                            </Chip>
                          </div>
                        </div>
                        <p className="mt-1 text-xs text-white/65 line-clamp-2">{item.body}</p>
                        <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                          {item.event_type} · {dayjs(item.created_at).format("YYYY-MM-DD HH:mm")}
                        </p>
                      </button>
                    );
                  })}
                  {!notificationsLoading && notificationRows.length === 0 ? (
                    <EmptyBlock
                      title="No notifications found"
                      description="There are no notifications for the current filter."
                    />
                  ) : null}
                </div>
              </Card>
            </>
          ) : (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>Notification reading is restricted.</p>
              </div>
            </Card>
          )}

          {notificationsError ? (
            <ErrorBlock
              title="Failed to load notifications"
              description={extractApiErrorMessage(notificationsError)}
              onRetry={() => Promise.all([refreshNotifications(), refreshUnread()])}
            />
          ) : null}
        </section>

        <section className="space-y-4">
          {selectedNotification ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="cb-title text-xl">Details</p>
                <Chip color={severityChipColor(selectedNotification.severity)} variant="flat">
                  {selectedNotification.severity}
                </Chip>
              </div>
              <p className="mt-3 text-sm text-white/90">{selectedNotification.title}</p>
              <p className="mt-2 text-sm text-white/75">{selectedNotification.body}</p>
              <div className="mt-3 space-y-1 text-xs text-white/60">
                <p>Public ID: {selectedNotification.public_id}</p>
                <p>Event: {selectedNotification.event_type}</p>
                <p>Category: {selectedNotification.category}</p>
                <p>Entity: {selectedNotification.entity_type || "-"} / {selectedNotification.entity_public_id || "-"}</p>
                <p>Created: {dayjs(selectedNotification.created_at).format("YYYY-MM-DD HH:mm")}</p>
              </div>
              {selectedNotification.metadata_json ? (
                <pre className="mt-3 max-h-56 overflow-auto rounded-xl border border-white/10 bg-white/5 p-3 text-[11px] text-white/75">
                  {JSON.stringify(selectedNotification.metadata_json, null, 2)}
                </pre>
              ) : null}
              {!selectedNotification.is_read && canRead ? (
                <Button
                  className="mt-3"
                  variant="flat"
                  color="warning"
                  onPress={() => handleMarkRead(selectedNotification.public_id)}
                >
                  Mark Read
                </Button>
              ) : null}
              {canRead ? (
                <Button className="mt-2" variant="ghost" onPress={() => handleDelete(selectedNotification.public_id)}>
                  Delete
                </Button>
              ) : null}
            </Card>
          ) : null}

          {canBroadcast ? (
            <FormSectionDisclosure title="Broadcast Notification" defaultExpanded>
              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="mb-3 flex items-center gap-2">
                <Megaphone size={15} className="text-amber-200" />
                <p className="cb-title text-xl">Broadcast Notification</p>
              </div>
              <form className="space-y-3" onSubmit={handleBroadcast}>
                <FormInput
                  name="eventType"
                  placeholder="event_type (e.g. roster.promoted)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="category"
                  placeholder="category (e.g. roster)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormSelect
                  name="severity"
                  defaultValue="info"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                >
                  <option value="info">info</option>
                  <option value="success">success</option>
                  <option value="warning">warning</option>
                  <option value="critical">critical</option>
                </FormSelect>
                <FormInput
                  name="title"
                  placeholder="Title"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormTextarea
                  name="body"
                  rows={3}
                  placeholder="Body"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="entityType"
                  placeholder="entity_type (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="entityPublicId"
                  placeholder="entity_public_id (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormTextarea
                  rows={4}
                  value={metadataRaw}
                  onChange={(event) => setMetadataRaw(event.target.value)}
                  placeholder="metadata_json as JSON"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 font-mono text-xs text-white"
                />
                <Button type="submit" color="warning" startContent={<Send size={14} />}>
                  Send Broadcast
                </Button>
              </form>
            </Card>
            </FormSectionDisclosure>
          ) : null}

          {canTargeted ? (
            <FormSectionDisclosure title="Targeted Notification">
              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="mb-3 flex items-center gap-2">
                <Megaphone size={15} className="text-amber-200" />
                <p className="cb-title text-xl">Targeted Notification</p>
              </div>
              <form className="space-y-3" onSubmit={handleTargetedSend}>
                <FormInput
                  name="eventType"
                  placeholder="event_type"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="category"
                  placeholder="category"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormSelect
                  name="severity"
                  defaultValue="info"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                >
                  <option value="info">info</option>
                  <option value="success">success</option>
                  <option value="warning">warning</option>
                  <option value="critical">critical</option>
                </FormSelect>
                <FormInput
                  name="title"
                  placeholder="Title"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormTextarea
                  name="body"
                  rows={3}
                  placeholder="Body"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="userIds"
                  placeholder="User IDs (comma-separated)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="roleIds"
                  placeholder="Role IDs (comma-separated)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="entityType"
                  placeholder="entity_type (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="entityPublicId"
                  placeholder="entity_public_id (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button type="submit" color="warning" startContent={<Send size={14} />}>
                  Send Targeted
                </Button>
              </form>
            </Card>
            </FormSectionDisclosure>
          ) : null}
        </section>
      </div>
    </div>
  );
}
