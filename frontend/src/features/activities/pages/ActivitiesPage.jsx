import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import {
  CalendarClock,
  CheckCircle2,
  CircleX,
  ExternalLink,
  Megaphone,
  Plus,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { toast } from "sonner";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { FormInput, FormSelect, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import {
  approveActivity,
  createActivity,
  listActivities,
  publishActivity,
  rejectActivity,
} from "../api/activities-api.js";

function statusChipColor(status) {
  const value = String(status || "").toLowerCase();
  if (["approved", "posted"].includes(value)) return "success";
  if (["pending", "scheduled"].includes(value)) return "warning";
  if (["rejected", "publish_failed"].includes(value)) return "danger";
  return "default";
}

function normalizeActivityRows(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (Array.isArray(payload?.items)) {
    return payload.items;
  }
  if (Array.isArray(payload?.data)) {
    return payload.data;
  }
  return [];
}

export function ActivitiesPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["activities.read"], permissions, isOwner);
  const canCreate = hasPermissionSet(["activities.create"], permissions, isOwner);
  const canApprove = hasPermissionSet(["activities.approve"], permissions, isOwner);
  const canReject = hasPermissionSet(["activities.reject"], permissions, isOwner);
  const canPublish = hasPermissionSet(["activities.publish_forum"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(
    [
      "activities.read",
      "activities.create",
      "activities.approve",
      "activities.reject",
      "activities.publish_forum",
    ],
    permissions,
    isOwner,
  );

  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [selectedPublicId, setSelectedPublicId] = useState("");
  const [reviewComment, setReviewComment] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [forumTopicId, setForumTopicId] = useState("");
  const [forceRetry, setForceRetry] = useState(false);

  const {
    data: activities,
    error: activitiesError,
    isLoading: activitiesLoading,
    mutate: refreshActivities,
  } = useSWR(
    canRead ? ["activities-list", statusFilter || "all", typeFilter || "all"] : null,
    () =>
      listActivities({
        status: statusFilter || undefined,
        activityType: typeFilter || undefined,
        limit: 100,
        offset: 0,
      }),
  );

  const activityRows = useMemo(() => normalizeActivityRows(activities), [activities]);

  const selectedActivity = useMemo(
    () => activityRows.find((row) => row.public_id === selectedPublicId) || null,
    [activityRows, selectedPublicId],
  );

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Activities Access Restricted"
        description="You need activities permissions to use this page."
      />
    );
  }

  async function handleCreate(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const createScheduledFor = String(form.get("scheduledFor") || "").trim();
    const payload = {
      activity_type: String(form.get("activityType") || "").trim(),
      title: String(form.get("title") || "").trim(),
      duration_minutes: Number(form.get("durationMinutes") || 0),
      notes: String(form.get("notes") || "").trim() || null,
      scheduled_for: createScheduledFor
        ? new Date(createScheduledFor).toISOString()
        : null,
    };
    if (
      !payload.activity_type ||
      !payload.title ||
      !Number.isFinite(payload.duration_minutes) ||
      payload.duration_minutes <= 0
    ) {
      toast.error("Type, title, and valid duration are required");
      return;
    }
    try {
      const created = await createActivity(payload);
      toast.success(`Activity created: ${created.public_id}`);
      formElement?.reset?.();
      await refreshActivities();
      setSelectedPublicId(created.public_id);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to create activity"));
    }
  }

  async function handleApprove() {
    if (!selectedPublicId) {
      toast.error("Select an activity first");
      return;
    }
    try {
      await approveActivity(selectedPublicId, {
        approval_comment: reviewComment.trim() || null,
        scheduled_for: scheduledFor ? new Date(scheduledFor).toISOString() : null,
      });
      toast.success("Activity approved");
      await refreshActivities();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to approve activity"));
    }
  }

  async function handleReject() {
    if (!selectedPublicId) {
      toast.error("Select an activity first");
      return;
    }
    try {
      await rejectActivity(selectedPublicId, {
        approval_comment: reviewComment.trim() || null,
      });
      toast.success("Activity rejected");
      await refreshActivities();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to reject activity"));
    }
  }

  async function handlePublish() {
    if (!selectedPublicId) {
      toast.error("Select an activity first");
      return;
    }
    try {
      await publishActivity(selectedPublicId, {
        forum_topic_id: forumTopicId.trim() || null,
        force_retry: forceRetry,
      });
      toast.success("Publish command sent");
      await refreshActivities();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to publish activity"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Patrols / Trainings
              </Chip>
              <Chip variant="flat" startContent={<CalendarClock size={13} />}>
                Approval + publish workflow
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Activities</h2>
          </div>
          {canRead ? (
            <Button
              variant="ghost"
              startContent={<RefreshCw size={15} />}
              onPress={() => refreshActivities()}
            >
              Refresh
            </Button>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-4">
          {canRead ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="flex flex-wrap items-center gap-3">
                <label className="text-sm text-white/80">Status</label>
                <FormSelect
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  className="rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                >
                  <option value="">All</option>
                  <option value="pending">pending</option>
                  <option value="approved">approved</option>
                  <option value="scheduled">scheduled</option>
                  <option value="rejected">rejected</option>
                  <option value="posted">posted</option>
                  <option value="publish_failed">publish_failed</option>
                </FormSelect>
                <label className="text-sm text-white/80">Type</label>
                <FormInput
                  value={typeFilter}
                  onChange={(event) => setTypeFilter(event.target.value)}
                  placeholder="patrol / training / event"
                  className="rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
              </div>
            </Card>
          ) : null}

          {canRead ? (
            <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
              <div className="mb-2 flex items-center justify-between px-2 py-1">
                <p className="text-sm text-white/70">
                  Activities: <span className="font-semibold text-white">{activityRows.length}</span>
                </p>
                {activitiesLoading ? <p className="text-xs text-white/55">Loading...</p> : null}
              </div>
              <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
                {activityRows.map((activity) => {
                  const active = activity.public_id === selectedPublicId;
                  return (
                    <button
                      key={activity.public_id}
                      type="button"
                      onClick={() => setSelectedPublicId(activity.public_id)}
                      className={[
                        "w-full rounded-xl border p-3 text-left transition",
                        active
                          ? "border-amber-300/45 bg-amber-300/15"
                          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                      ].join(" ")}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-white">
                          {activity.public_id} · {activity.title}
                        </p>
                        <Chip size="sm" color={statusChipColor(activity.status)} variant="flat">
                          {activity.status}
                        </Chip>
                      </div>
                      <p className="mt-1 text-xs text-white/65">
                        {activity.activity_type} · {activity.duration_minutes}m
                      </p>
                      <p className="mt-1 text-xs text-white/70 line-clamp-2">{activity.notes || "No notes"}</p>
                      <div className="mt-2 flex items-center justify-between gap-2 text-[11px] uppercase tracking-[0.16em] text-white/45">
                        <span>Created {dayjs(activity.created_at).format("YYYY-MM-DD HH:mm")}</span>
                        <Link
                          to={`/activities/${activity.public_id}`}
                          className="inline-flex items-center gap-1 text-amber-200 hover:text-amber-100"
                        >
                          Open <ExternalLink size={12} />
                        </Link>
                      </div>
                    </button>
                  );
                })}
                {!activitiesLoading && activityRows.length === 0 ? (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                    No activities found.
                  </div>
                ) : null}
              </div>
            </Card>
          ) : (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>Read access is restricted. You can still run allowed write actions.</p>
              </div>
            </Card>
          )}

          {activitiesError ? (
            <Card className="border border-rose-300/25 bg-rose-300/10 p-3">
              <p className="text-sm text-rose-100">
                {extractApiErrorMessage(activitiesError, "Failed to load activities")}
              </p>
            </Card>
          ) : null}
        </section>

        <section className="space-y-4">
          {canCreate ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Create Activity</p>
              <form className="space-y-3" onSubmit={handleCreate}>
                <FormInput
                  name="activityType"
                  placeholder="Type (patrol/training/event)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="title"
                  placeholder="Title"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="durationMinutes"
                  type="number"
                  min={1}
                  defaultValue={30}
                  placeholder="Duration minutes"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="scheduledFor"
                  type="datetime-local"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormTextarea
                  name="notes"
                  rows={3}
                  placeholder="Notes"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button type="submit" color="warning" startContent={<Plus size={14} />}>
                  Create Activity
                </Button>
              </form>
            </Card>
          ) : null}

          {selectedActivity && (canApprove || canReject) ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Review Activity {selectedActivity.public_id}</p>
              <FormTextarea
                rows={3}
                value={reviewComment}
                onChange={(event) => setReviewComment(event.target.value)}
                placeholder="Review comment"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <FormInput
                type="datetime-local"
                value={scheduledFor}
                onChange={(event) => setScheduledFor(event.target.value)}
                className="mt-3 w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <div className="mt-3 flex flex-wrap gap-2">
                {canApprove ? (
                  <Button
                    color="warning"
                    variant="flat"
                    startContent={<CheckCircle2 size={14} />}
                    onPress={handleApprove}
                  >
                    Approve / Schedule
                  </Button>
                ) : null}
                {canReject ? (
                  <Button
                    color="danger"
                    variant="flat"
                    startContent={<CircleX size={14} />}
                    onPress={handleReject}
                  >
                    Reject
                  </Button>
                ) : null}
              </div>
            </Card>
          ) : null}

          {selectedActivity && canPublish ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Publish to Forum</p>
              <FormInput
                value={forumTopicId}
                onChange={(event) => setForumTopicId(event.target.value)}
                placeholder="Forum topic ID (optional if already set)"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <label className="mt-3 inline-flex items-center gap-2 text-sm text-white/80">
                <FormInput
                  type="checkbox"
                  checked={forceRetry}
                  onChange={(event) => setForceRetry(event.target.checked)}
                />
                Force retry if already posted
              </label>
              <Button
                className="mt-3"
                color="warning"
                variant="flat"
                startContent={<Megaphone size={14} />}
                onPress={handlePublish}
              >
                Publish
              </Button>
            </Card>
          ) : null}

          {!canCreate && !canApprove && !canReject && !canPublish ? (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>You currently have read-only access for activities.</p>
              </div>
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
