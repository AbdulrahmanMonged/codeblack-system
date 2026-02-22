import { Button, Card, Chip } from "@heroui/react";
import { FormInput, FormSelect, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { DashboardSearchField } from "../../../shared/ui/DashboardSearchField.jsx";
import { ListPaginationBar } from "../../../shared/ui/ListPaginationBar.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import dayjs from "dayjs";
import { Plus, RefreshCw, Users2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { toArray } from "../../../shared/utils/collections.js";
import { includesSearchQuery } from "../../../shared/utils/search.js";
import {
  createRank,
  createRosterMembership,
  listRanks,
  listRoster,
  updateRosterMembership,
} from "../api/roster-api.js";

function statusChipColor(status) {
  const value = String(status || "").toLowerCase();
  if (["active", "approved"].includes(value)) return "success";
  if (["pending", "under_review", "on_leave"].includes(value)) return "warning";
  if (["inactive", "removed", "left"].includes(value)) return "danger";
  return "default";
}

export function RosterManagementPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canReadRoster = hasAnyPermissionSet(["roster.read", "ranks.read"], permissions, isOwner);
  const canWriteRoster = hasPermissionSet(["roster.write"], permissions, isOwner);
  const canWriteRanks = hasPermissionSet(["ranks.write"], permissions, isOwner);

  const [selectedMembershipId, setSelectedMembershipId] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [membershipStatus, setMembershipStatus] = useState("active");
  const [membershipNotes, setMembershipNotes] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const { data: memberships, error: rosterError, mutate: refreshRoster, isLoading: rosterLoading } = useSWR(
    canReadRoster ? ["roster-memberships", page, pageSize] : null,
    () => listRoster({ limit: pageSize + 1, offset: (page - 1) * pageSize }),
  );
  const { data: ranks, error: ranksError, mutate: refreshRanks } = useSWR(
    canReadRoster ? ["roster-ranks"] : null,
    () => listRanks(),
  );

  const membershipRows = useMemo(() => toArray(memberships), [memberships]);
  const pageMembershipRows = useMemo(() => membershipRows.slice(0, pageSize), [membershipRows, pageSize]);
  const hasNextPage = membershipRows.length > pageSize;
  const filteredMembershipRows = useMemo(
    () =>
      pageMembershipRows.filter((row) =>
        includesSearchQuery(row, searchQuery, [
          "membership_id",
          "player_id",
          "player.ingame_name",
          "player.account_name",
          "display_rank",
          "status",
        ]),
      ),
    [pageMembershipRows, searchQuery],
  );
  const rankRows = useMemo(() => toArray(ranks), [ranks]);
  const selectedMembership = useMemo(
    () => pageMembershipRows.find((row) => String(row.membership_id) === String(selectedMembershipId)) || null,
    [pageMembershipRows, selectedMembershipId],
  );

  useEffect(() => {
    if (searchQuery.trim()) {
      setPage(1);
    }
  }, [searchQuery]);

  if (!canReadRoster) {
    return (
      <ForbiddenState
        title="Roster Access Restricted"
        description="You need roster.read permission to view roster records."
      />
    );
  }

  async function handleCreateRank(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      name: String(form.get("name") || "").trim(),
      level: Number(form.get("level") || 1),
    };
    if (!payload.name) {
      toast.error("Rank name is required.");
      return;
    }
    try {
      await createRank(payload);
      toast.success("Rank created");
      formElement?.reset?.();
      await refreshRanks();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to create rank"));
    }
  }

  async function handleCreateMembership(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      player_id: Number(form.get("playerId") || 0),
      status: String(form.get("status") || "active"),
      current_rank_id: form.get("rankId") ? Number(form.get("rankId")) : null,
      display_rank: String(form.get("displayRank") || "").trim() || null,
      is_on_leave: String(form.get("isOnLeave") || "") === "on",
      notes: String(form.get("notes") || "").trim() || null,
    };
    if (!Number.isFinite(payload.player_id) || payload.player_id <= 0) {
      toast.error("Valid player id is required.");
      return;
    }
    try {
      await createRosterMembership(payload);
      toast.success("Membership created");
      formElement?.reset?.();
      await refreshRoster();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to create membership"));
    }
  }

  async function handleUpdateMembership() {
    if (!selectedMembershipId) {
      toast.error("Select a membership first.");
      return;
    }
    try {
      await updateRosterMembership(Number(selectedMembershipId), {
        status: membershipStatus,
        notes: membershipNotes.trim() || null,
      });
      toast.success("Membership updated");
      await refreshRoster();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to update membership"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">CodeBlack</Chip>
              <Chip variant="flat" startContent={<Users2 size={13} />}>Roster + ranks</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Roster Management</h2>
          </div>
          <Button variant="ghost" startContent={<RefreshCw size={15} />} onPress={() => refreshRoster()}>
            Refresh
          </Button>
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-4">
          <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
            <div className="mb-2 flex items-center justify-between px-2 py-1">
              <p className="text-sm text-white/70">
                Memberships: <span className="font-semibold text-white">{filteredMembershipRows.length}</span>
              </p>
              {rosterLoading ? <p className="text-xs text-white/55">Loading...</p> : null}
            </div>
            <div className="mb-3">
              <DashboardSearchField
                label="Search Memberships"
                description="Search by membership ID, player ID, in-game nickname, or account name."
                placeholder="Search roster members..."
                value={searchQuery}
                onChange={setSearchQuery}
                className="w-full"
                inputClassName="w-full"
              />
            </div>
            <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
              {filteredMembershipRows.map((row) => (
                <button
                  key={row.membership_id}
                  type="button"
                  onClick={() => {
                    setSelectedMembershipId(String(row.membership_id));
                    setMembershipStatus(String(row.status || "active"));
                    setMembershipNotes(String(row.notes || ""));
                  }}
                  className={[
                    "w-full rounded-xl border p-3 text-left transition",
                    String(row.membership_id) === String(selectedMembershipId)
                      ? "border-amber-300/45 bg-amber-300/15"
                      : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                  ].join(" ")}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-white">
                      {row.player?.ingame_name || "-"} ({row.player?.account_name || "-"})
                    </p>
                    <Chip size="sm" color={statusChipColor(row.status)} variant="flat">
                      {row.status}
                    </Chip>
                  </div>
                  <p className="mt-1 text-xs text-white/65">
                    Rank: {row.display_rank || "-"} · Leave: {row.is_on_leave ? "Yes" : "No"}
                  </p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                    Membership #{row.membership_id} · Updated {dayjs(row.updated_at).format("YYYY-MM-DD HH:mm")}
                  </p>
                </button>
              ))}
            </div>
            {!rosterLoading && filteredMembershipRows.length === 0 ? (
              <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                No memberships matched the current search query.
              </div>
            ) : null}
            <ListPaginationBar
              page={page}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={(nextPageSize) => {
                setPageSize(nextPageSize);
                setPage(1);
              }}
              hasNextPage={hasNextPage}
              isLoading={rosterLoading}
              visibleCount={filteredMembershipRows.length}
            />
          </Card>
          {rosterError ? (
            <Card className="border border-rose-300/25 bg-rose-300/10 p-3">
              <p className="text-sm text-rose-100">
                {extractApiErrorMessage(rosterError, "Failed to load roster")}
              </p>
            </Card>
          ) : null}
        </section>

        <section className="space-y-4">
          {canWriteRoster ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <FormSectionDisclosure
  title={<><span className="inline-flex items-center gap-2">
                      <Plus size={14} />
                      Create Membership
                    </span></>}
>
<form className="space-y-3" onSubmit={handleCreateMembership}>
                <FormInput
                  name="playerId"
                  type="number"
                  min={1}
                  placeholder="Player ID"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormSelect
                  name="status"
                  defaultValue="active"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                >
                  <option value="active">active</option>
                  <option value="on_leave">on_leave</option>
                  <option value="inactive">inactive</option>
                </FormSelect>
                <FormInput
                  name="rankId"
                  type="number"
                  min={1}
                  placeholder="Current rank id (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="displayRank"
                  placeholder="Display rank (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput name="isOnLeave" type="checkbox">
                  Is on leave
                </FormInput>
                <FormTextarea
                  name="notes"
                  rows={3}
                  placeholder="Notes"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button type="submit" color="warning" startContent={<Plus size={14} />}>
                  Create Membership
                </Button>
                    </form>
</FormSectionDisclosure>
            </Card>
          ) : null}

          {selectedMembership && canWriteRoster ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <FormSectionDisclosure
  title={<><span className="inline-flex items-center gap-2">
                      <Users2 size={14} />
                      Update Membership #{selectedMembership.membership_id}
                    </span></>}
>
<div className="space-y-3">
                <FormSelect
                  value={membershipStatus}
                  onChange={(event) => setMembershipStatus(event.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                >
                  <option value="active">active</option>
                  <option value="on_leave">on_leave</option>
                  <option value="inactive">inactive</option>
                  <option value="left">left</option>
                  <option value="kicked">kicked</option>
                </FormSelect>
                <FormTextarea
                  rows={3}
                  value={membershipNotes}
                  onChange={(event) => setMembershipNotes(event.target.value)}
                  placeholder="Update notes"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button color="warning" onPress={handleUpdateMembership}>Save Membership</Button>
                    </div>
</FormSectionDisclosure>
            </Card>
          ) : null}

          {canWriteRanks ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <FormSectionDisclosure
  title={<><span className="inline-flex items-center gap-2">
                      <Plus size={14} />
                      Create Rank
                    </span></>}
>
<form className="space-y-3" onSubmit={handleCreateRank}>
                <FormInput
                  name="name"
                  placeholder="Rank name"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="level"
                  type="number"
                  min={1}
                  defaultValue={1}
                  placeholder="Rank level"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button type="submit" color="warning" startContent={<Plus size={14} />}>
                  Create Rank
                </Button>
                    </form>
</FormSectionDisclosure>
            </Card>
          ) : null}

          <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
            <p className="mb-2 cb-title text-xl">Ranks</p>
            <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
              {rankRows.map((rank) => (
                <div key={rank.id} className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/85">
                  <div className="flex items-center justify-between gap-2">
                    <p>{rank.name}</p>
                    <Chip size="sm" variant="flat">Lv {rank.level}</Chip>
                  </div>
                </div>
              ))}
              {!rankRows.length ? (
                <p className="text-sm text-white/65">No ranks configured yet.</p>
              ) : null}
            </div>
            {ranksError ? (
              <p className="mt-2 text-sm text-rose-200">
                {extractApiErrorMessage(ranksError, "Failed to load ranks")}
              </p>
            ) : null}
          </Card>
        </section>
      </div>
    </div>
  );
}
