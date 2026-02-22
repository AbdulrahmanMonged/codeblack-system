import { Button, Card, Chip } from "@heroui/react";
import { FormInput, FormSelect, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import dayjs from "dayjs";
import {
  CheckCheck,
  CheckCircle2,
  CircleX,
  Filter,
  LoaderCircle,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { isValidElement, useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasPermissionSet } from "../../../core/permissions/guards.js";
import { getActivityByPublicId, approveActivity, rejectActivity } from "../../activities/api/activities-api.js";
import {
  approveBlacklistRemovalRequest,
  denyBlacklistRemovalRequest,
  getBlacklistRemovalRequestById,
  listBlacklistRemovalRequests,
} from "../../blacklist/api/blacklist-api.js";
import { getReviewQueue } from "../api/admin-api.js";
import { getApplicationByPublicId, decideApplication } from "../../applications/api/applications-api.js";
import { listConfigChanges, approveConfigChange } from "../../config-registry/api/config-registry-api.js";
import { getOrderByPublicId, decideOrder } from "../../orders/api/orders-api.js";
import { getVacationByPublicId, approveVacation, denyVacation } from "../../vacations/api/vacations-api.js";
import {
  approveVerificationRequest,
  denyVerificationRequest,
  getVerificationRequestByPublicId,
} from "../../verification/api/verification-api.js";

const REVIEW_TYPES = [
  { key: "applications", label: "Applications" },
  { key: "orders", label: "Orders" },
  { key: "activities", label: "Activities" },
  { key: "vacations", label: "Vacations" },
  { key: "blacklist_removals", label: "Blacklist Removals" },
  { key: "verification_requests", label: "Verification Requests" },
  { key: "config_changes", label: "Config Changes" },
];
const BLACKLIST_REMOVAL_PAGE_LIMIT = 100;
const BLACKLIST_REMOVAL_SCAN_MAX = 1000;

function statusColor(status) {
  const value = String(status || "").toLowerCase();
  if (
    ["submitted", "pending", "under_review", "pending_approval", "scheduled"].includes(
      value,
    )
  ) {
    return "warning";
  }
  if (["approved", "accepted", "posted", "completed", "returned"].includes(value)) {
    return "success";
  }
  if (["declined", "denied", "rejected", "removed", "cancelled"].includes(value)) {
    return "danger";
  }
  return "default";
}

async function resolveBlacklistRemovalByPublicId(publicId) {
  const pendingMatch = await findBlacklistRemovalByPublicId(publicId, "pending");
  if (pendingMatch) {
    return pendingMatch;
  }
  return findBlacklistRemovalByPublicId(publicId);
}

async function findBlacklistRemovalByPublicId(publicId, status) {
  let offset = 0;
  while (offset < BLACKLIST_REMOVAL_SCAN_MAX) {
    const rows = await listBlacklistRemovalRequests({
      status,
      limit: BLACKLIST_REMOVAL_PAGE_LIMIT,
      offset,
    });
    const match = (rows || []).find((row) => row.public_id === publicId);
    if (match) {
      return match;
    }
    if (!Array.isArray(rows) || rows.length < BLACKLIST_REMOVAL_PAGE_LIMIT) {
      break;
    }
    offset += BLACKLIST_REMOVAL_PAGE_LIMIT;
  }
  return null;
}

async function resolveConfigChangeById(changeId) {
  const rows = await listConfigChanges({ limit: 200 });
  return rows.find((row) => String(row.id) === String(changeId)) ?? null;
}

async function fetchQueueDetail(itemType, itemId) {
  switch (itemType) {
    case "applications":
      return getApplicationByPublicId(itemId);
    case "orders":
      return getOrderByPublicId(itemId);
    case "activities":
      return getActivityByPublicId(itemId);
    case "vacations":
      return getVacationByPublicId(itemId);
    case "blacklist_removals": {
      const match = await resolveBlacklistRemovalByPublicId(itemId);
      if (!match) {
        throw new Error("Blacklist removal request could not be resolved by public id");
      }
      const detail = await getBlacklistRemovalRequestById(match.id);
      return { ...detail, _request_id: match.id };
    }
    case "config_changes": {
      const match = await resolveConfigChangeById(itemId);
      if (!match) {
        throw new Error("Config change could not be resolved");
      }
      return match;
    }
    case "verification_requests": {
      return getVerificationRequestByPublicId(itemId);
    }
    default:
      return null;
  }
}

function InfoRow({ label, value }) {
  function renderValue() {
    if (value === null || value === undefined || value === "") {
      return "-";
    }
    if (isValidElement(value)) {
      return value;
    }
    if (typeof value === "object") {
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    }
    return String(value);
  }

  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/10 py-2 text-sm">
      <span className="text-white/60">{label}</span>
      <span className="max-w-[70%] text-right text-white/90">{renderValue()}</span>
    </div>
  );
}

export function ReviewQueuePage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [pendingOnly, setPendingOnly] = useState(true);
  const [selectedTypes, setSelectedTypes] = useState(() =>
    REVIEW_TYPES.map((item) => item.key),
  );
  const [selectedKey, setSelectedKey] = useState("");
  const [decisionReason, setDecisionReason] = useState("");
  const [reapplyPolicy, setReapplyPolicy] = useState("allow_immediate");
  const [cooldownDays, setCooldownDays] = useState("7");
  const [scheduledFor, setScheduledFor] = useState("");
  const [isDeciding, setIsDeciding] = useState(false);

  const queueKey = useMemo(
    () => [
      "review-queue",
      selectedTypes.join(","),
      status || "",
      search || "",
      pendingOnly ? "1" : "0",
    ],
    [pendingOnly, search, selectedTypes, status],
  );

  const {
    data: queueData,
    error: queueError,
    isLoading: queueLoading,
    mutate: refreshQueue,
  } = useSWR(queueKey, () =>
    getReviewQueue({
      itemTypes: selectedTypes,
      status: status || undefined,
      search: search || undefined,
      pendingOnly,
      limit: 80,
      offset: 0,
    }),
  );

  const selectedItem = useMemo(() => {
    const items = queueData?.items || [];
    return items.find((item) => `${item.item_type}:${item.item_id}` === selectedKey) || null;
  }, [queueData?.items, selectedKey]);

  useEffect(() => {
    if (!queueData?.items?.length) {
      setSelectedKey("");
      return;
    }
    const keyExists = queueData.items.some(
      (item) => `${item.item_type}:${item.item_id}` === selectedKey,
    );
    if (!keyExists) {
      const first = queueData.items[0];
      setSelectedKey(`${first.item_type}:${first.item_id}`);
    }
  }, [queueData, selectedKey]);

  useEffect(() => {
    setDecisionReason("");
    setReapplyPolicy("allow_immediate");
    setCooldownDays("7");
    setScheduledFor("");
  }, [selectedKey]);

  const {
    data: detail,
    error: detailError,
    isLoading: detailLoading,
    mutate: refreshDetail,
  } = useSWR(
    selectedItem
      ? ["review-detail", selectedItem.item_type, selectedItem.item_id]
      : null,
    ([, itemType, itemId]) => fetchQueueDetail(itemType, itemId),
  );

  function toggleType(typeKey) {
    setSelectedTypes((previous) => {
      if (previous.includes(typeKey)) {
        if (previous.length === 1) {
          return previous;
        }
        return previous.filter((value) => value !== typeKey);
      }
      return [...previous, typeKey];
    });
  }

  function can(requiredPermissions) {
    return hasPermissionSet(requiredPermissions, permissions, isOwner);
  }

  async function runDecision(action) {
    if (!selectedItem) {
      return;
    }
    setIsDeciding(true);
    try {
      switch (selectedItem.item_type) {
        case "applications": {
          const isAccept = action === "accept";
          if (!decisionReason.trim()) {
            throw new Error("Decision reason is required");
          }
          const payload = {
            decision: isAccept ? "accepted" : "declined",
            decision_reason: decisionReason.trim(),
            reapply_policy: isAccept ? "allow_immediate" : reapplyPolicy,
            cooldown_days:
              !isAccept && reapplyPolicy === "cooldown"
                ? Number(cooldownDays || 0)
                : null,
          };
          await decideApplication(selectedItem.item_id, payload);
          break;
        }
        case "orders": {
          const isAccept = action === "accept";
          if (!isAccept && !decisionReason.trim()) {
            throw new Error("Denial reason is required");
          }
          await decideOrder(selectedItem.item_id, {
            decision: isAccept ? "accepted" : "denied",
            reason: decisionReason.trim() || null,
          });
          break;
        }
        case "activities": {
          const payload = {
            approval_comment: decisionReason.trim() || null,
            scheduled_for: action === "approve" && scheduledFor ? new Date(scheduledFor).toISOString() : null,
          };
          if (action === "approve") {
            await approveActivity(selectedItem.item_id, payload);
          } else {
            await rejectActivity(selectedItem.item_id, payload);
          }
          break;
        }
        case "vacations": {
          const payload = {
            review_comment: decisionReason.trim() || null,
          };
          if (action === "approve") {
            await approveVacation(selectedItem.item_id, payload);
          } else {
            await denyVacation(selectedItem.item_id, payload);
          }
          break;
        }
        case "blacklist_removals": {
          const mappedRequestId = detail?._request_id;
          if (!mappedRequestId) {
            throw new Error("Could not resolve blacklist removal request id");
          }
          const payload = {
            review_comment: decisionReason.trim() || null,
          };
          if (action === "approve") {
            await approveBlacklistRemovalRequest(mappedRequestId, payload);
          } else {
            await denyBlacklistRemovalRequest(mappedRequestId, payload);
          }
          break;
        }
        case "config_changes": {
          const changeId = Number(selectedItem.item_id);
          if (!Number.isFinite(changeId)) {
            throw new Error("Invalid config change id");
          }
          const reason = decisionReason.trim() || "Approved from review queue";
          await approveConfigChange(changeId, { change_reason: reason });
          break;
        }
        case "verification_requests": {
          if (action === "approve") {
            await approveVerificationRequest(selectedItem.item_id, {
              review_comment: decisionReason.trim() || null,
            });
          } else {
            if (!decisionReason.trim()) {
              throw new Error("Review comment is required for denial");
            }
            await denyVerificationRequest(selectedItem.item_id, {
              review_comment: decisionReason.trim(),
            });
          }
          break;
        }
        default:
          throw new Error(`Unsupported queue item: ${selectedItem.item_type}`);
      }

      toast.success("Review action completed");
      await Promise.all([refreshQueue(), refreshDetail()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Review action failed"));
    } finally {
      setIsDeciding(false);
    }
  }

  function renderDetailSection() {
    if (!selectedItem) {
      return (
        <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
          No queue item selected.
        </div>
      );
    }

    if (detailLoading) {
      return (
        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/75">
          <LoaderCircle size={15} className="animate-spin" />
          Loading detail...
        </div>
      );
    }

    if (detailError) {
      return (
        <div className="rounded-xl border border-rose-300/25 bg-rose-300/10 p-4 text-sm text-rose-100">
          {extractApiErrorMessage(detailError, "Failed to load item details")}
        </div>
      );
    }

    switch (selectedItem.item_type) {
      case "applications":
        return (
          <div className="space-y-1">
            <InfoRow label="Public ID" value={detail?.public_id} />
            <InfoRow label="Status" value={detail?.status} />
            <InfoRow label="Account" value={detail?.account_name} />
            <InfoRow label="Nickname" value={detail?.in_game_nickname} />
            <InfoRow label="English Skill" value={detail?.english_skill} />
            <InfoRow label="Submitter Type" value={detail?.submitter_type} />
            <InfoRow label="Submitted" value={dayjs(detail?.submitted_at).format("YYYY-MM-DD HH:mm")} />
          </div>
        );
      case "orders":
        return (
          <div className="space-y-1">
            <InfoRow label="Public ID" value={detail?.public_id} />
            <InfoRow label="Status" value={detail?.status} />
            <InfoRow label="Account" value={detail?.account_name} />
            <InfoRow label="In-game Name" value={detail?.ingame_name} />
            <InfoRow label="Submitted" value={dayjs(detail?.submitted_at).format("YYYY-MM-DD HH:mm")} />
            <InfoRow
              label="Proof"
              value={
                detail?.proof_file_url ? (
                  <a href={detail.proof_file_url} target="_blank" rel="noreferrer" className="underline">
                    Open proof
                  </a>
                ) : (
                  "-"
                )
              }
            />
          </div>
        );
      case "activities":
        return (
          <div className="space-y-1">
            <InfoRow label="Public ID" value={detail?.public_id} />
            <InfoRow label="Status" value={detail?.status} />
            <InfoRow label="Type" value={detail?.activity_type} />
            <InfoRow label="Title" value={detail?.title} />
            <InfoRow label="Duration" value={`${detail?.duration_minutes || 0} mins`} />
            <InfoRow
              label="Scheduled"
              value={
                detail?.scheduled_for
                  ? dayjs(detail.scheduled_for).format("YYYY-MM-DD HH:mm")
                  : "-"
              }
            />
          </div>
        );
      case "vacations":
        return (
          <div className="space-y-1">
            <InfoRow label="Public ID" value={detail?.public_id} />
            <InfoRow label="Status" value={detail?.status} />
            <InfoRow label="Player ID" value={detail?.player_id} />
            <InfoRow label="Leave Date" value={detail?.leave_date} />
            <InfoRow label="Expected Return" value={detail?.expected_return_date} />
            <InfoRow label="Target Group" value={detail?.target_group || "-"} />
          </div>
        );
      case "blacklist_removals":
        return (
          <div className="space-y-1">
            <InfoRow label="Public ID" value={detail?.public_id} />
            <InfoRow label="Status" value={detail?.status} />
            <InfoRow label="Account Name" value={detail?.account_name} />
            <InfoRow label="Requested At" value={dayjs(detail?.requested_at).format("YYYY-MM-DD HH:mm")} />
            <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/85">
              <p className="mb-1 text-xs uppercase tracking-[0.16em] text-white/55">Request Text</p>
              <p>{detail?.request_text || "-"}</p>
            </div>
          </div>
        );
      case "config_changes":
        return (
          <div className="space-y-1">
            <InfoRow label="Change ID" value={detail?.id} />
            <InfoRow label="Config Key" value={detail?.config_key} />
            <InfoRow label="Status" value={detail?.status} />
            <InfoRow label="Changed By" value={detail?.changed_by_user_id || "-"} />
            <InfoRow label="Created" value={dayjs(detail?.created_at).format("YYYY-MM-DD HH:mm")} />
            <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/85">
              <p className="mb-1 text-xs uppercase tracking-[0.16em] text-white/55">Change Reason</p>
              <p>{detail?.change_reason || "-"}</p>
            </div>
          </div>
        );
      case "verification_requests":
        return (
          <div className="space-y-1">
            <InfoRow label="Public ID" value={detail?.public_id} />
            <InfoRow label="Status" value={detail?.status} />
            <InfoRow label="Account" value={detail?.account_name} />
            <InfoRow label="Serial" value={detail?.mta_serial} />
            <InfoRow label="Forum URL" value={detail?.forum_url} />
            <InfoRow label="Requested At" value={dayjs(detail?.created_at).format("YYYY-MM-DD HH:mm")} />
            <InfoRow label="Review Comment" value={detail?.review_comment || "-"} />
          </div>
        );
      default:
        return null;
    }
  }

  function renderActionSection() {
    if (!selectedItem) {
      return null;
    }

    const itemType = selectedItem.item_type;
    const isApplication = itemType === "applications";
    const isOrder = itemType === "orders";
    const isActivity = itemType === "activities";
    const isVacation = itemType === "vacations";
    const isBlacklistRemoval = itemType === "blacklist_removals";
    const isVerification = itemType === "verification_requests";
    const isConfigChange = itemType === "config_changes";

    return (
      <div className="space-y-3 rounded-xl border border-white/10 bg-white/5 p-4">
        <p className="text-xs uppercase tracking-[0.18em] text-white/55">Decision Panel</p>

        {(isApplication ||
          isOrder ||
          isActivity ||
          isVacation ||
          isBlacklistRemoval ||
          isVerification ||
          isConfigChange) && (
          <div className="space-y-1">
            <label className="text-sm text-white/80">Review comment / reason</label>
            <FormTextarea
              rows={4}
              value={decisionReason}
              onChange={(event) => setDecisionReason(event.target.value)}
              className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2.5 text-sm text-white outline-none focus:border-amber-300/60"
              placeholder="Explain your decision"
            />
          </div>
        )}

        {isApplication ? (
          <div className="space-y-3 rounded-xl border border-white/10 bg-black/40 p-3">
            <p className="text-sm text-white/70">Decline policy controls</p>
            <div className="grid gap-3 md:grid-cols-2">
              <FormSelect
                value={reapplyPolicy}
                onChange={(event) => setReapplyPolicy(event.target.value)}
                className="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-white"
              >
                <option value="allow_immediate">Allow immediate</option>
                <option value="cooldown">Cooldown</option>
                <option value="permanent_block">Permanent block</option>
              </FormSelect>
              <FormInput
                type="number"
                min={1}
                max={365}
                value={cooldownDays}
                onChange={(event) => setCooldownDays(event.target.value)}
                disabled={reapplyPolicy !== "cooldown"}
                className="rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-white disabled:opacity-45"
                placeholder="Cooldown days"
              />
            </div>
          </div>
        ) : null}

        {isActivity ? (
          <div className="space-y-1">
            <label className="text-sm text-white/80">Schedule time for approval (optional)</label>
            <FormInput
              type="datetime-local"
              value={scheduledFor}
              onChange={(event) => setScheduledFor(event.target.value)}
              className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2.5 text-sm text-white"
            />
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {isApplication ? (
            <>
              <Button
                color="success"
                variant="flat"
                isDisabled={!can(["applications.review", "applications.decision.accept"]) || isDeciding}
                onPress={() => runDecision("accept")}
                startContent={<CheckCircle2 size={15} />}
              >
                Accept
              </Button>
              <Button
                color="danger"
                variant="flat"
                isDisabled={!can(["applications.review", "applications.decision.decline"]) || isDeciding}
                onPress={() => runDecision("decline")}
                startContent={<CircleX size={15} />}
              >
                Decline
              </Button>
            </>
          ) : null}

          {isOrder ? (
            <>
              <Button
                color="success"
                variant="flat"
                isDisabled={!can(["orders.review", "orders.decision.accept"]) || isDeciding}
                onPress={() => runDecision("accept")}
                startContent={<CheckCircle2 size={15} />}
              >
                Accept
              </Button>
              <Button
                color="danger"
                variant="flat"
                isDisabled={!can(["orders.review", "orders.decision.deny"]) || isDeciding}
                onPress={() => runDecision("deny")}
                startContent={<CircleX size={15} />}
              >
                Deny
              </Button>
            </>
          ) : null}

          {isActivity ? (
            <>
              <Button
                color="success"
                variant="flat"
                isDisabled={!can(["activities.approve"]) || isDeciding}
                onPress={() => runDecision("approve")}
                startContent={<CheckCircle2 size={15} />}
              >
                Approve
              </Button>
              <Button
                color="danger"
                variant="flat"
                isDisabled={!can(["activities.reject"]) || isDeciding}
                onPress={() => runDecision("reject")}
                startContent={<CircleX size={15} />}
              >
                Reject
              </Button>
            </>
          ) : null}

          {isVacation ? (
            <>
              <Button
                color="success"
                variant="flat"
                isDisabled={!can(["vacations.approve"]) || isDeciding}
                onPress={() => runDecision("approve")}
                startContent={<CheckCircle2 size={15} />}
              >
                Approve
              </Button>
              <Button
                color="danger"
                variant="flat"
                isDisabled={!can(["vacations.deny"]) || isDeciding}
                onPress={() => runDecision("deny")}
                startContent={<CircleX size={15} />}
              >
                Deny
              </Button>
            </>
          ) : null}

          {isBlacklistRemoval ? (
            <>
              <Button
                color="success"
                variant="flat"
                isDisabled={!can(["blacklist_removal_requests.review"]) || isDeciding}
                onPress={() => runDecision("approve")}
                startContent={<CheckCircle2 size={15} />}
              >
                Approve
              </Button>
              <Button
                color="danger"
                variant="flat"
                isDisabled={!can(["blacklist_removal_requests.review"]) || isDeciding}
                onPress={() => runDecision("deny")}
                startContent={<CircleX size={15} />}
              >
                Deny
              </Button>
            </>
          ) : null}

          {isConfigChange ? (
            <Button
              color="success"
              variant="flat"
              isDisabled={!can(["config_change.approve"]) || isDeciding}
              onPress={() => runDecision("approve")}
              startContent={<CheckCheck size={15} />}
            >
              Approve Change
            </Button>
          ) : null}

          {isVerification ? (
            <>
              <Button
                color="success"
                variant="flat"
                isDisabled={!can(["verification_requests.review"]) || isDeciding}
                onPress={() => runDecision("approve")}
                startContent={<CheckCircle2 size={15} />}
              >
                Approve
              </Button>
              <Button
                color="danger"
                variant="flat"
                isDisabled={!can(["verification_requests.review"]) || isDeciding}
                onPress={() => runDecision("deny")}
                startContent={<CircleX size={15} />}
              >
                Deny
              </Button>
            </>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Staff Workflow
              </Chip>
              <Chip variant="flat" startContent={<Filter size={13} />}>
                Unified review queue
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Review Queue</h2>
            <p className="mt-1 text-sm text-white/75">
              Moderate pending items across applications, orders, activities, vacations, and more.
            </p>
          </div>
          <Button
            variant="ghost"
            onPress={() => refreshQueue()}
            isLoading={queueLoading}
            startContent={<RefreshCw size={15} />}
          >
            Refresh Queue
          </Button>
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-4">
          <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
            <div className="grid gap-3 md:grid-cols-[1fr_auto_auto]">
              <div className="relative">
                <Search
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/50"
                />
                <FormInput
                  type="text"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      setSearch(searchInput.trim());
                    }
                  }}
                  placeholder="Search by ID/account/title..."
                  className="w-full rounded-xl border border-white/15 bg-black/40 py-2 pl-9 pr-3 text-sm text-white outline-none focus:border-amber-300/60"
                />
              </div>
              <FormSelect
                value={status}
                onChange={(event) => setStatus(event.target.value)}
                className="rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              >
                <option value="">Any status</option>
                <option value="submitted">submitted</option>
                <option value="pending">pending</option>
                <option value="under_review">under_review</option>
                <option value="approved">approved</option>
                <option value="declined">declined</option>
                <option value="denied">denied</option>
                <option value="rejected">rejected</option>
                <option value="pending_approval">pending_approval</option>
              </FormSelect>
              <Button type="button" variant="ghost" onPress={() => setSearch(searchInput.trim())}>
                Apply
              </Button>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-2">
              {REVIEW_TYPES.map((typeItem) => {
                const active = selectedTypes.includes(typeItem.key);
                return (
                  <Button
                    key={typeItem.key}
                    size="sm"
                    variant={active ? "solid" : "ghost"}
                    color={active ? "warning" : "default"}
                    onPress={() => toggleType(typeItem.key)}
                  >
                    {typeItem.label}
                  </Button>
                );
              })}
              <label className="ml-auto inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-white/80">
                <FormInput
                  type="checkbox"
                  checked={pendingOnly}
                  onChange={(event) => setPendingOnly(event.target.checked)}
                />
                Pending only
              </label>
            </div>
          </Card>

          {queueError ? (
            <Card className="border border-rose-300/25 bg-rose-300/10 p-4 shadow-2xl backdrop-blur-xl">
              <p className="text-sm text-rose-100">
                {extractApiErrorMessage(queueError, "Failed to load review queue")}
              </p>
            </Card>
          ) : null}

          <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
            <div className="mb-2 flex items-center justify-between px-2 py-1">
              <p className="text-sm text-white/70">
                Items: <span className="font-semibold text-white">{queueData?.total || 0}</span>
              </p>
              {queueLoading ? (
                <p className="text-xs text-white/55">Loading...</p>
              ) : null}
            </div>

            <div className="max-h-[60vh] space-y-2 overflow-y-auto pr-1">
              {(queueData?.items || []).map((item) => {
                const key = `${item.item_type}:${item.item_id}`;
                const isActive = key === selectedKey;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelectedKey(key)}
                    className={[
                      "w-full rounded-xl border p-3 text-left transition",
                      isActive
                        ? "border-amber-300/45 bg-amber-300/15"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                    ].join(" ")}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-white">{item.title}</p>
                      <Chip size="sm" color={statusColor(item.status)} variant="flat">
                        {item.status}
                      </Chip>
                    </div>
                    <p className="mt-1 text-xs text-white/65">{item.subtitle || item.item_type}</p>
                    <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                      {item.item_type} · {item.item_id} ·{" "}
                      {dayjs(item.queued_at).format("YYYY-MM-DD HH:mm")}
                    </p>
                  </button>
                );
              })}
              {!queueLoading && (queueData?.items || []).length === 0 ? (
                <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                  No items matched the current filters.
                </div>
              ) : null}
            </div>
          </Card>
        </section>

        <section className="space-y-4">
          <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
            <div className="mb-3 flex items-center justify-between gap-2">
              <p className="cb-title text-xl">Selected Item</p>
              {selectedItem ? (
                <Chip size="sm" color={statusColor(selectedItem.status)} variant="flat">
                  {selectedItem.status}
                </Chip>
              ) : null}
            </div>

            {selectedItem ? (
              <div className="mb-3 rounded-xl border border-white/10 bg-white/5 p-3 text-xs text-white/60">
                {selectedItem.item_type} · {selectedItem.item_id}
              </div>
            ) : null}

            {renderDetailSection()}
          </Card>

          <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
            <div className="mb-3 flex items-center gap-2">
              <ShieldAlert size={15} className="text-amber-200" />
              <p className="text-sm text-white/80">
                Decision actions enforce backend permissions and workflows.
              </p>
            </div>
            {renderActionSection()}
          </Card>
        </section>
      </div>
    </div>
  );
}
