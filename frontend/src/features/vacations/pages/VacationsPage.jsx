import { Button, Card, Chip, Separator } from "@heroui/react";
import dayjs from "dayjs";
import {
  CalendarArrowUp,
  CalendarCheck2,
  CircleX,
  Plus,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import {
  selectCurrentUser,
  selectIsOwner,
  selectPermissions,
} from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { FormInput, FormSelect, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { DashboardSearchField } from "../../../shared/ui/DashboardSearchField.jsx";
import { ListPaginationBar } from "../../../shared/ui/ListPaginationBar.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import { includesSearchQuery } from "../../../shared/utils/search.js";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import {
  approveVacation,
  cancelVacation,
  createVacation,
  denyVacation,
  getVacationPolicies,
  listMyVacations,
  listVacations,
  markVacationReturned,
} from "../api/vacations-api.js";

function statusChipColor(status) {
  const value = String(status || "").toLowerCase();
  if (["approved", "returned"].includes(value)) return "success";
  if (["pending"].includes(value)) return "warning";
  if (["denied", "cancelled"].includes(value)) return "danger";
  return "default";
}

export function VacationsPage() {
  const currentUser = useAppSelector(selectCurrentUser);
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["vacations.read"], permissions, isOwner);
  const canSubmit = hasPermissionSet(["vacations.submit"], permissions, isOwner);
  const canApprove = hasPermissionSet(["vacations.approve"], permissions, isOwner);
  const canDeny = hasPermissionSet(["vacations.deny"], permissions, isOwner);
  const canCancel = hasPermissionSet(["vacations.cancel"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(
    ["vacations.read", "vacations.submit", "vacations.approve", "vacations.deny", "vacations.cancel"],
    permissions,
    isOwner,
  );

  const canReadAll = canRead;
  const canReadMine = canRead || canSubmit;

  const [statusFilter, setStatusFilter] = useState("");
  const [playerFilter, setPlayerFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPublicId, setSelectedPublicId] = useState("");
  const [reviewComment, setReviewComment] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const { data: policies } = useSWR(canReadMine ? ["vacation-policies"] : null, () =>
    getVacationPolicies(),
  );

  const {
    data: vacations,
    error: vacationsError,
    isLoading: vacationsLoading,
    mutate: refreshVacations,
  } = useSWR(
    canReadMine
      ? [
          "vacations-list",
          canReadAll ? "all" : "mine",
          statusFilter || "all",
          playerFilter || "all",
          page,
          pageSize,
        ]
      : null,
    () => {
      const payload = {
        status: statusFilter || undefined,
        limit: pageSize + 1,
        offset: (page - 1) * pageSize,
      };
      if (canReadAll) {
        return listVacations({
          ...payload,
          playerId: playerFilter ? Number(playerFilter) : undefined,
        });
      }
      return listMyVacations(payload);
    },
  );

  const vacationRows = useMemo(() => (Array.isArray(vacations) ? vacations : []), [vacations]);
  const pageVacationRows = useMemo(() => vacationRows.slice(0, pageSize), [vacationRows, pageSize]);
  const hasNextPage = vacationRows.length > pageSize;

  const filteredVacationRows = useMemo(
    () =>
      pageVacationRows.filter((vacation) =>
        includesSearchQuery(vacation, searchQuery, [
          "public_id",
          "player_id",
          "status",
          "target_group",
          "reason",
          "leave_date",
          "expected_return_date",
        ]),
      ),
    [pageVacationRows, searchQuery],
  );

  const selectedVacation = useMemo(
    () => pageVacationRows.find((row) => row.public_id === selectedPublicId) || null,
    [pageVacationRows, selectedPublicId],
  );

  const canCancelOwnSelected =
    canCancel &&
    selectedVacation &&
    selectedVacation.requester_user_id === Number(currentUser?.userId);

  useEffect(() => {
    setPage(1);
  }, [statusFilter, playerFilter]);

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Vacation Access Restricted"
        description="You need vacation permissions to use this page."
      />
    );
  }

  async function handleCreate(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const leaveDate = String(form.get("leaveDate") || "").trim();
    const returnDate = String(form.get("expectedReturnDate") || "").trim();
    const payload = {
      leave_date: leaveDate,
      expected_return_date: returnDate,
      target_group: String(form.get("targetGroup") || "").trim() || null,
      reason: String(form.get("reason") || "").trim() || null,
    };
    if (!leaveDate || !returnDate) {
      toast.error("Leave date and return date are required");
      return;
    }
    const durationDays = dayjs(returnDate).diff(dayjs(leaveDate), "day") + 1;
    if (durationDays <= 0) {
      toast.error("Return date must be on or after leave date");
      return;
    }
    if (policies?.max_duration_days && durationDays > policies.max_duration_days) {
      toast.error(`Vacation exceeds max duration (${policies.max_duration_days} days)`);
      return;
    }
    try {
      const created = await createVacation(payload);
      toast.success(`Vacation request submitted: ${created.public_id}`);
      formElement?.reset?.();
      await refreshVacations();
      setSelectedPublicId(created.public_id);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to submit vacation request"));
    }
  }

  async function handleApprove() {
    if (!selectedPublicId) {
      toast.error("Select a request first");
      return;
    }
    try {
      await approveVacation(selectedPublicId, {
        review_comment: reviewComment.trim() || null,
      });
      toast.success("Vacation approved");
      await refreshVacations();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to approve vacation"));
    }
  }

  async function handleDeny() {
    if (!selectedPublicId) {
      toast.error("Select a request first");
      return;
    }
    if (!reviewComment.trim()) {
      toast.error("Review comment is required to deny");
      return;
    }
    try {
      await denyVacation(selectedPublicId, {
        review_comment: reviewComment.trim(),
      });
      toast.success("Vacation denied");
      await refreshVacations();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to deny vacation"));
    }
  }

  async function handleMarkReturned() {
    if (!selectedPublicId) {
      toast.error("Select a request first");
      return;
    }
    try {
      await markVacationReturned(selectedPublicId, {
        review_comment: reviewComment.trim() || null,
      });
      toast.success("Vacation marked as returned");
      await refreshVacations();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to mark return"));
    }
  }

  async function handleCancel() {
    if (!selectedPublicId) {
      toast.error("Select a request first");
      return;
    }
    try {
      await cancelVacation(selectedPublicId);
      toast.success("Vacation cancelled");
      await refreshVacations();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to cancel vacation"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Vacation Workflow
              </Chip>
              <Chip variant="flat" startContent={<CalendarArrowUp size={13} />}>
                Request + review
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Vacations</h2>
          </div>
          {canReadMine ? (
            <Button
              variant="ghost"
              startContent={<RefreshCw size={15} />}
              onPress={() => refreshVacations()}
            >
              Refresh
            </Button>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-4">
          {canReadMine ? (
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
                  <option value="denied">denied</option>
                  <option value="returned">returned</option>
                  <option value="cancelled">cancelled</option>
                </FormSelect>

                {canReadAll ? (
                  <>
                    <label className="text-sm text-white/80">Player ID</label>
                    <FormInput
                      value={playerFilter}
                      onChange={(event) => setPlayerFilter(event.target.value)}
                      placeholder="filter by player id"
                      className="rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                    />
                  </>
                ) : (
                  <p className="text-xs text-white/60">Showing your own vacation requests only.</p>
                )}
              </div>
              <div className="mt-3">
                <DashboardSearchField
                  label="Search Vacations"
                  description="Search by request ID, player/account info, status, and reason."
                  placeholder="Search vacation requests..."
                  value={searchQuery}
                  onChange={setSearchQuery}
                  className="w-full"
                  inputClassName="w-full"
                />
              </div>
              <p className="mt-2 text-xs text-white/60">
                Max duration policy: {policies?.max_duration_days || 7} days
              </p>
            </Card>
          ) : null}

          {canReadMine ? (
            <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
              <div className="mb-2 flex items-center justify-between px-2 py-1">
                <p className="text-sm text-white/70">
                  Requests: <span className="font-semibold text-white">{filteredVacationRows.length}</span>
                </p>
                {vacationsLoading ? <p className="text-xs text-white/55">Loading...</p> : null}
              </div>
              <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
                {filteredVacationRows.map((vacation) => {
                  const active = vacation.public_id === selectedPublicId;
                  return (
                    <button
                      key={vacation.public_id}
                      type="button"
                      onClick={() => setSelectedPublicId(vacation.public_id)}
                      className={[
                        "w-full rounded-xl border p-3 text-left transition",
                        active
                          ? "border-amber-300/45 bg-amber-300/15"
                          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                      ].join(" ")}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-white">{vacation.public_id}</p>
                        <Chip size="sm" color={statusChipColor(vacation.status)} variant="flat">
                          {vacation.status}
                        </Chip>
                      </div>
                      <p className="mt-1 text-xs text-white/65">
                        Player #{vacation.player_id} · {vacation.leave_date} → {vacation.expected_return_date}
                      </p>
                      <p className="mt-1 text-xs text-white/70 line-clamp-2">
                        {vacation.reason || "No reason supplied"}
                      </p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                        Created {dayjs(vacation.created_at).format("YYYY-MM-DD HH:mm")}
                      </p>
                    </button>
                  );
                })}
                {!vacationsLoading && filteredVacationRows.length === 0 ? (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                    No vacation requests found.
                  </div>
                ) : null}
              </div>
              <ListPaginationBar
                page={page}
                pageSize={pageSize}
                onPageChange={setPage}
                onPageSizeChange={(nextPageSize) => {
                  setPageSize(nextPageSize);
                  setPage(1);
                }}
                hasNextPage={hasNextPage}
                isLoading={vacationsLoading}
                visibleCount={filteredVacationRows.length}
              />
            </Card>
          ) : (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>Vacation listing is restricted. Submit actions may still be available.</p>
              </div>
            </Card>
          )}

          {vacationsError ? (
            <Card className="border border-rose-300/25 bg-rose-300/10 p-3">
              <p className="text-sm text-rose-100">
                {extractApiErrorMessage(vacationsError, "Failed to load vacations")}
              </p>
            </Card>
          ) : null}
        </section>

        <section className="space-y-4">
          {canSubmit ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <FormSectionDisclosure
                title={
                  <>
                    <span className="inline-flex items-center gap-2">
                      <Plus size={14} />
                      Submit Vacation Request
                    </span>
                  </>
                }
              >
                <form className="space-y-3" onSubmit={handleCreate}>
                  <FormInput
                    name="leaveDate"
                    type="date"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                  <FormInput
                    name="expectedReturnDate"
                    type="date"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                  <FormInput
                    name="targetGroup"
                    placeholder="Target group while away (optional)"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                  <FormTextarea
                    name="reason"
                    rows={3}
                    placeholder="Reason (optional)"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                  <Button type="submit" color="warning" startContent={<Plus size={14} />}>
                    Submit Request
                  </Button>
                </form>
              </FormSectionDisclosure>
            </Card>
          ) : null}

          {selectedVacation && (canApprove || canDeny || canCancel) ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <FormSectionDisclosure
                title={
                  <>
                    <span className="inline-flex items-center gap-2">
                      <CalendarCheck2 size={14} />
                      Review Request {selectedVacation.public_id}
                    </span>
                  </>
                }
              >
                <FormTextarea
                  rows={3}
                  value={reviewComment}
                  onChange={(event) => setReviewComment(event.target.value)}
                  placeholder="Reviewer comment"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  {canApprove ? (
                    <>
                      <Button
                        color="warning"
                        variant="flat"
                        startContent={<CalendarCheck2 size={14} />}
                        onPress={handleApprove}
                      >
                        Approve
                      </Button>
                      <Separator orientation="vertical" className="h-5 bg-white/20" />
                      <Button
                        variant="flat"
                        startContent={<CalendarArrowUp size={14} />}
                        onPress={handleMarkReturned}
                      >
                        Mark Returned
                      </Button>
                      {canDeny || canCancelOwnSelected ? (
                        <Separator orientation="vertical" className="h-5 bg-white/20" />
                      ) : null}
                    </>
                  ) : null}
                  {canDeny ? (
                    <>
                      <Button
                      color="danger"
                      variant="flat"
                      startContent={<CircleX size={14} />}
                      onPress={handleDeny}
                    >
                      Deny
                    </Button>
                    {canCancelOwnSelected ? <Separator orientation="vertical" className="h-5 bg-white/20" /> : null}
                    </>
                  ) : null}
                  {canCancelOwnSelected ? (
                    <Button variant="ghost" onPress={handleCancel}>
                      Cancel Own Request
                    </Button>
                  ) : null}
                </div>
              </FormSectionDisclosure>
            </Card>
          ) : null}

          {!canSubmit && !canApprove && !canDeny && !canCancel ? (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>You currently have read-only vacation access.</p>
              </div>
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
