import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import {
  CheckCircle2,
  CircleX,
  Megaphone,
  RefreshCw,
  ShieldAlert,
  UserPlus,
} from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import useSWR from "swr";
import { toast } from "sonner";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { FormInput, FormSelect, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import {
  addActivityParticipant,
  approveActivity,
  getActivityByPublicId,
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

export function ActivityDetailPage() {
  const { publicId = "" } = useParams();
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["activities.read"], permissions, isOwner);
  const canApprove = hasPermissionSet(["activities.approve"], permissions, isOwner);
  const canReject = hasPermissionSet(["activities.reject"], permissions, isOwner);
  const canPublish = hasPermissionSet(["activities.publish_forum"], permissions, isOwner);
  const canManageParticipants = hasPermissionSet(
    ["activities.manage_participants"],
    permissions,
    isOwner,
  );
  const canAccess = hasAnyPermissionSet(
    [
      "activities.read",
      "activities.approve",
      "activities.reject",
      "activities.publish_forum",
      "activities.manage_participants",
    ],
    permissions,
    isOwner,
  );

  const [reviewComment, setReviewComment] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [forumTopicId, setForumTopicId] = useState("");
  const [forceRetry, setForceRetry] = useState(false);

  const {
    data: activity,
    error: activityError,
    isLoading: activityLoading,
    mutate: refreshActivity,
  } = useSWR(
    canRead && publicId ? ["activity-detail", publicId] : null,
    ([, id]) => getActivityByPublicId(id),
  );

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Activity Access Restricted"
        description="You need activity permissions to access this route."
      />
    );
  }

  async function handleApprove() {
    if (!publicId) {
      return;
    }
    try {
      await approveActivity(publicId, {
        approval_comment: reviewComment.trim() || null,
        scheduled_for: scheduledFor ? new Date(scheduledFor).toISOString() : null,
      });
      toast.success("Activity approved");
      await refreshActivity();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to approve activity"));
    }
  }

  async function handleReject() {
    if (!publicId) {
      return;
    }
    try {
      await rejectActivity(publicId, {
        approval_comment: reviewComment.trim() || null,
      });
      toast.success("Activity rejected");
      await refreshActivity();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to reject activity"));
    }
  }

  async function handlePublish() {
    if (!publicId) {
      return;
    }
    try {
      await publishActivity(publicId, {
        forum_topic_id: forumTopicId.trim() || null,
        force_retry: forceRetry,
      });
      toast.success("Publish command sent");
      await refreshActivity();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to publish activity"));
    }
  }

  async function handleAddParticipant(event) {
    event.preventDefault();
    if (!publicId) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      player_id: Number(form.get("playerId") || 0),
      participant_role: String(form.get("participantRole") || "participant").trim(),
      attendance_status: String(form.get("attendanceStatus") || "planned").trim(),
      notes: String(form.get("notes") || "").trim() || null,
    };
    if (!Number.isFinite(payload.player_id) || payload.player_id <= 0) {
      toast.error("Valid player id is required");
      return;
    }
    try {
      await addActivityParticipant(publicId, payload);
      toast.success("Participant added");
      formElement?.reset?.();
      await refreshActivity();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to add participant"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Activity Details
              </Chip>
              <Chip variant="flat">ID {publicId}</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Activity {publicId}</h2>
          </div>
          <div className="flex items-center gap-2">
            {canRead ? (
              <Button
                variant="ghost"
                startContent={<RefreshCw size={15} />}
                onPress={() => refreshActivity()}
              >
                Refresh
              </Button>
            ) : null}
            <Button as={Link} to="/activities" variant="flat">
              Back
            </Button>
          </div>
        </div>
      </Card>

      {activityLoading ? (
        <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
          <p className="text-sm text-white/70">Loading activity...</p>
        </Card>
      ) : null}

      {activityError ? (
        <Card className="border border-rose-300/25 bg-rose-300/10 p-4">
          <p className="text-sm text-rose-100">
            {extractApiErrorMessage(activityError, "Failed to load activity")}
          </p>
        </Card>
      ) : null}

      {activity ? (
        <Card className="border border-white/15 bg-black/45 p-5 shadow-2xl backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="cb-title text-2xl">{activity.title}</p>
            <Chip color={statusChipColor(activity.status)} variant="flat">
              {activity.status}
            </Chip>
          </div>
          <div className="mt-3 grid gap-2 text-sm text-white/80 md:grid-cols-2">
            <p>Type: {activity.activity_type}</p>
            <p>Duration: {activity.duration_minutes} minutes</p>
            <p>Created by user: {activity.created_by_user_id}</p>
            <p>Scheduled: {activity.scheduled_for ? dayjs(activity.scheduled_for).format("YYYY-MM-DD HH:mm") : "-"}</p>
            <p>Forum topic: {activity.forum_topic_id || "-"}</p>
          </div>
          <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/75">
            {activity.notes || "No notes"}
          </p>
          {activity.last_publish_error ? (
            <p className="mt-2 text-xs text-rose-200">Last publish error: {activity.last_publish_error}</p>
          ) : null}
        </Card>
      ) : null}

      {(canApprove || canReject) && publicId ? (
        <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
          <p className="mb-3 cb-title text-xl">Review Actions</p>
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

      {canPublish && publicId ? (
        <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
          <p className="mb-3 cb-title text-xl">Publish Actions</p>
          <FormInput
            value={forumTopicId}
            onChange={(event) => setForumTopicId(event.target.value)}
            placeholder="Forum topic ID (optional)"
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

      {canManageParticipants && publicId ? (
        <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
          <p className="mb-3 cb-title text-xl">Participants</p>
          {activity?.participants?.length ? (
            <div className="mb-3 space-y-2">
              {activity.participants.map((participant) => (
                <div
                  key={participant.id}
                  className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80"
                >
                  Player #{participant.player_id} · {participant.participant_role} ·{" "}
                  {participant.attendance_status}
                </div>
              ))}
            </div>
          ) : null}
          <form className="space-y-3" onSubmit={handleAddParticipant}>
            <FormInput
              name="playerId"
              type="number"
              min={1}
              placeholder="Player ID"
              className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
            />
            <FormInput
              name="participantRole"
              placeholder="participant role (participant/leader)"
              defaultValue="participant"
              className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
            />
            <FormInput
              name="attendanceStatus"
              placeholder="attendance status (planned/attended)"
              defaultValue="planned"
              className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
            />
            <FormTextarea
              name="notes"
              rows={2}
              placeholder="Notes"
              className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
            />
            <Button type="submit" variant="ghost" startContent={<UserPlus size={14} />}>
              Add Participant
            </Button>
          </form>
        </Card>
      ) : null}

      {!canRead ? (
        <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
          <div className="flex items-start gap-3 text-sm text-white/80">
            <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
            <p>activities.read is missing, so detail data may be unavailable for this route.</p>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
