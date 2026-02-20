import { Avatar, Button, Card, Chip } from "@heroui/react";
import { FormInput, FormSelect, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import dayjs from "dayjs";
import {
  CheckCircle2,
  CircleX,
  LockKeyhole,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Unlock,
  Users,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import useSWR from "swr";
import { toast } from "sonner";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import {
  castApplicationVote,
  castVote,
  closeVoting,
  decideApplicationFromVoting,
  getVotingContext,
  listApplicationVoters,
  listVotingVoters,
  reopenVoting,
  resetVoting,
} from "../api/voting-api.js";

function statusChipColor(status) {
  const value = String(status || "").toLowerCase();
  if (value === "open") return "success";
  if (value === "closed") return "danger";
  return "default";
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

export function VotingContextPage() {
  const { contextType = "", contextId = "", applicationId = "" } = useParams();
  const resolvedContextType = applicationId ? "application" : contextType;
  const resolvedContextId = applicationId || contextId;
  const isApplicationContext = resolvedContextType === "application";

  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["voting.read"], permissions, isOwner);
  const canCast = hasPermissionSet(["voting.cast"], permissions, isOwner);
  const canListVoters = hasPermissionSet(["voting.list_voters"], permissions, isOwner);
  const canClose = hasPermissionSet(["voting.close"], permissions, isOwner);
  const canReopen = hasPermissionSet(["voting.reopen"], permissions, isOwner);
  const canReset = hasPermissionSet(["voting.reset"], permissions, isOwner);
  const canReviewApplications = hasPermissionSet(["applications.review"], permissions, isOwner);
  const canAcceptApplication =
    isOwner || hasPermissionSet(["applications.decision.accept"], permissions, isOwner);
  const canDeclineApplication =
    isOwner || hasPermissionSet(["applications.decision.decline"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(
    ["voting.read", "voting.cast", "voting.list_voters", "voting.close", "voting.reopen", "voting.reset"],
    permissions,
    isOwner,
  );

  const [voteComment, setVoteComment] = useState("");
  const [moderationReason, setModerationReason] = useState("");
  const [reopenOnReset, setReopenOnReset] = useState(true);
  const [decisionReason, setDecisionReason] = useState("");
  const [reapplyPolicy, setReapplyPolicy] = useState("allow_immediate");
  const [cooldownDays, setCooldownDays] = useState("7");

  const {
    data: contextData,
    error: contextError,
    isLoading: contextLoading,
    mutate: refreshContext,
  } = useSWR(
    canRead && resolvedContextType && resolvedContextId
      ? ["voting-context", resolvedContextType, resolvedContextId]
      : null,
    ([, type, id]) => getVotingContext(type, id),
  );

  const {
    data: votersData,
    error: votersError,
    isLoading: votersLoading,
    mutate: refreshVoters,
  } = useSWR(
    canListVoters && resolvedContextId
      ? ["voting-voters", resolvedContextType, resolvedContextId]
      : null,
    ([, type, id]) =>
      type === "application" ? listApplicationVoters(id) : listVotingVoters(type, id),
  );

  const context = contextData || null;
  const voters = votersData?.voters || [];
  const yesPct =
    context?.counts?.total && context.counts.total > 0
      ? Math.round((context.counts.yes / context.counts.total) * 100)
      : 0;

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Voting Access Restricted"
        description="You need voting permissions to access this route."
      />
    );
  }

  async function handleVote(choice) {
    try {
      if (isApplicationContext) {
        await castApplicationVote(resolvedContextId, {
          choice,
          comment_text: voteComment.trim() || null,
        });
      } else {
        await castVote(resolvedContextType, resolvedContextId, {
          choice,
          comment_text: voteComment.trim() || null,
        });
      }
      setVoteComment("");
      toast.success(`Vote recorded: ${choice.toUpperCase()}`);
      await Promise.all([refreshContext(), refreshVoters()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to cast vote"));
    }
  }

  async function handleClose() {
    try {
      await closeVoting(resolvedContextType, resolvedContextId, {
        reason: moderationReason.trim() || null,
      });
      toast.success("Voting closed");
      await Promise.all([refreshContext(), refreshVoters()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to close voting"));
    }
  }

  async function handleReopen() {
    try {
      await reopenVoting(resolvedContextType, resolvedContextId, {
        reason: moderationReason.trim() || null,
      });
      toast.success("Voting reopened");
      await Promise.all([refreshContext(), refreshVoters()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to reopen voting"));
    }
  }

  async function handleReset() {
    try {
      await resetVoting(resolvedContextType, resolvedContextId, {
        reason: moderationReason.trim() || null,
        reopen: reopenOnReset,
      });
      toast.success("Voting reset");
      await Promise.all([refreshContext(), refreshVoters()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to reset voting"));
    }
  }

  async function handleDecision(decision) {
    if (!isApplicationContext) {
      return;
    }
    if (!decisionReason.trim()) {
      toast.error("Decision reason is required.");
      return;
    }
    const payload = {
      decision,
      decision_reason: decisionReason.trim(),
      reapply_policy: decision === "accepted" ? "allow_immediate" : reapplyPolicy,
      cooldown_days:
        decision === "declined" && reapplyPolicy === "cooldown"
          ? Number(cooldownDays || 0)
          : null,
    };
    try {
      await decideApplicationFromVoting(resolvedContextId, payload);
      toast.success(`Application ${decision}`);
      await Promise.all([refreshContext(), refreshVoters()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to finalize application"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">Voting Context</Chip>
              <Chip variant="flat">{resolvedContextType || "type"} / {resolvedContextId || "id"}</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Voting</h2>
          </div>
          {canRead ? (
            <Button variant="ghost" startContent={<RefreshCw size={15} />} onPress={() => refreshContext()}>
              Refresh
            </Button>
          ) : null}
        </div>
      </Card>

      {contextLoading ? (
        <Card className="border border-white/15 bg-black/45 p-4">
          <p className="text-sm text-white/70">Loading voting context...</p>
        </Card>
      ) : null}

      {contextError ? (
        <Card className="border border-rose-300/25 bg-rose-300/10 p-4">
          <p className="text-sm text-rose-100">
            {extractApiErrorMessage(contextError, "Failed to load voting context")}
          </p>
        </Card>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
        <section className="space-y-4">
          {context ? (
            <Card className="border border-white/15 bg-black/45 p-5 shadow-2xl backdrop-blur-xl">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="cb-title text-2xl">{context.title || "Untitled Context"}</p>
                <Chip color={statusChipColor(context.status)} variant="flat">{context.status}</Chip>
              </div>
              <div className="mt-3 grid gap-2 text-sm text-white/80 md:grid-cols-2">
                <p>Yes: {context.counts?.yes || 0}</p>
                <p>No: {context.counts?.no || 0}</p>
                <p>Total: {context.counts?.total || 0}</p>
                <p>Yes ratio: {yesPct}%</p>
                <p>Opened: {dayjs(context.opened_at).format("YYYY-MM-DD HH:mm")}</p>
                <p>Closed: {context.closed_at ? dayjs(context.closed_at).format("YYYY-MM-DD HH:mm") : "-"}</p>
              </div>
              <p className="mt-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/75">
                Your vote: <span className="font-semibold text-white">{context.my_vote || "not voted"}</span>
              </p>
              {context.close_reason ? (
                <p className="mt-2 text-xs text-white/65">Close reason: {context.close_reason}</p>
              ) : null}
            </Card>
          ) : (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>Context data unavailable.</p>
              </div>
            </Card>
          )}

          {canListVoters ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="mb-2 flex items-center justify-between">
                <p className="cb-title text-xl">Voters</p>
                <div className="flex items-center gap-2">
                  <Chip variant="flat" startContent={<Users size={12} />}>{voters.length}</Chip>
                  <Button size="sm" variant="ghost" onPress={() => refreshVoters()}>Refresh</Button>
                </div>
              </div>
              {votersLoading ? <p className="text-sm text-white/70">Loading voters...</p> : null}
              <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                {voters.map((voter) => (
                  <div
                    key={`${voter.user_id}-${voter.cast_at}`}
                    className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Avatar size="sm">
                          <Avatar.Image
                            alt={voter.username}
                            src={voter.avatar_url || undefined}
                          />
                          <Avatar.Fallback>{toInitials(voter.username)}</Avatar.Fallback>
                        </Avatar>
                        <p style={{ color: voter.name_color_hex || undefined }}>{voter.username}</p>
                      </div>
                      <Chip size="sm" variant="flat">{voter.choice}</Chip>
                    </div>
                    {voter.comment_text ? (
                      <p className="mt-1 text-xs text-white/70">Comment: {voter.comment_text}</p>
                    ) : null}
                    <p className="mt-1 text-xs text-white/60">
                      {dayjs(voter.updated_at).format("YYYY-MM-DD HH:mm")}
                    </p>
                  </div>
                ))}
                {!votersLoading && voters.length === 0 ? (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/70">
                    No votes yet.
                  </div>
                ) : null}
              </div>
              {votersError ? (
                <p className="mt-2 text-sm text-rose-200">
                  {extractApiErrorMessage(votersError, "Failed to load voters")}
                </p>
              ) : null}
            </Card>
          ) : null}
        </section>

        <section className="space-y-4">
          {canCast ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Cast Vote</p>
              <FormTextarea
                rows={3}
                value={voteComment}
                onChange={(event) => setVoteComment(event.target.value)}
                placeholder="Optional vote comment"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <div className="mt-3 flex flex-wrap gap-2">
                <Button color="warning" variant="flat" startContent={<CheckCircle2 size={14} />} onPress={() => handleVote("yes")}>
                  Vote YES
                </Button>
                <Button color="danger" variant="flat" startContent={<CircleX size={14} />} onPress={() => handleVote("no")}>
                  Vote NO
                </Button>
              </div>
            </Card>
          ) : null}

          {(canClose || canReopen || canReset) ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Moderation</p>
              <FormTextarea
                rows={3}
                value={moderationReason}
                onChange={(event) => setModerationReason(event.target.value)}
                placeholder="Reason (optional)"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <div className="mt-3 flex flex-wrap gap-2">
                {canClose ? (
                  <Button color="danger" variant="flat" startContent={<LockKeyhole size={14} />} onPress={handleClose}>
                    Close
                  </Button>
                ) : null}
                {canReopen ? (
                  <Button color="warning" variant="flat" startContent={<Unlock size={14} />} onPress={handleReopen}>
                    Reopen
                  </Button>
                ) : null}
              </div>
              {canReset ? (
                <>
                  <FormInput
                    className="mt-3"
                    type="checkbox"
                    checked={reopenOnReset}
                    onChange={(event) => setReopenOnReset(event.target.checked)}
                  >
                    Reopen context after reset
                  </FormInput>
                  <Button className="mt-3" variant="ghost" startContent={<RotateCcw size={14} />} onPress={handleReset}>
                    Reset Votes
                  </Button>
                </>
              ) : null}
            </Card>
          ) : null}

          {isApplicationContext && canReviewApplications ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Final Decision</p>
              <FormTextarea
                rows={3}
                value={decisionReason}
                onChange={(event) => setDecisionReason(event.target.value)}
                placeholder="Decision reason (required)"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <div className="mt-3 space-y-2">
                <FormSelect
                  value={reapplyPolicy}
                  onChange={(event) => setReapplyPolicy(event.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                >
                  <option value="allow_immediate">allow_immediate</option>
                  <option value="cooldown">cooldown</option>
                  <option value="permanent_block">permanent_block</option>
                </FormSelect>
                {reapplyPolicy === "cooldown" ? (
                  <FormInput
                    type="number"
                    min={1}
                    value={cooldownDays}
                    onChange={(event) => setCooldownDays(event.target.value)}
                    placeholder="Cooldown days"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                ) : null}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {canAcceptApplication ? (
                  <Button color="success" variant="flat" onPress={() => handleDecision("accepted")}>
                    Accept
                  </Button>
                ) : null}
                {canDeclineApplication ? (
                  <Button color="danger" variant="flat" onPress={() => handleDecision("declined")}>
                    Decline
                  </Button>
                ) : null}
              </div>
            </Card>
          ) : null}

          {!canCast && !canClose && !canReopen && !canReset ? (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>You currently have read-only voting access.</p>
              </div>
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
