import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import { Ban, CircleX, Plus, RefreshCw, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { FormInput, FormSelect, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import {
  createBlacklistEntry,
  listBlacklistEntries,
  removeBlacklistEntry,
  updateBlacklistEntry,
} from "../api/blacklist-api.js";

function statusChipColor(status) {
  const value = String(status || "").toLowerCase();
  if (value === "active") return "danger";
  if (value === "removed") return "success";
  if (value === "pending") return "warning";
  return "default";
}

export function BlacklistManagementPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["blacklist.read"], permissions, isOwner);
  const canAdd = hasPermissionSet(["blacklist.add"], permissions, isOwner);
  const canUpdate = hasPermissionSet(["blacklist.update"], permissions, isOwner);
  const canRemove = hasPermissionSet(["blacklist.remove"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(
    ["blacklist.read", "blacklist.add", "blacklist.update", "blacklist.remove"],
    permissions,
    isOwner,
  );

  const [statusFilter, setStatusFilter] = useState("");
  const [selectedEntryId, setSelectedEntryId] = useState("");
  const [updateLevel, setUpdateLevel] = useState("1");
  const [updateAlias, setUpdateAlias] = useState("");
  const [updateSerial, setUpdateSerial] = useState("");
  const [updateRoots, setUpdateRoots] = useState("");
  const [updateRemarks, setUpdateRemarks] = useState("");
  const [removalReason, setRemovalReason] = useState("");

  const {
    data: entries,
    error: entriesError,
    isLoading: entriesLoading,
    mutate: refreshEntries,
  } = useSWR(
    canRead ? ["blacklist-entries", statusFilter || "all"] : null,
    () =>
      listBlacklistEntries({
        status: statusFilter || undefined,
        limit: 100,
        offset: 0,
      }),
  );

  const selectedEntry = useMemo(
    () => (entries || []).find((row) => String(row.id) === String(selectedEntryId)) || null,
    [entries, selectedEntryId],
  );

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Blacklist Access Restricted"
        description="You need blacklist permissions to access this page."
      />
    );
  }

  async function handleCreateEntry(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const playerIdRaw = String(form.get("playerId") || "").trim();
    const payload = {
      player_id: playerIdRaw ? Number(playerIdRaw) : null,
      blacklist_level: Number(form.get("level") || 1),
      alias: String(form.get("alias") || "").trim(),
      identity: String(form.get("identity") || "").trim(),
      serial: String(form.get("serial") || "").trim() || null,
      roots: String(form.get("roots") || "")
        .trim()
        .toUpperCase() || null,
      remarks: String(form.get("remarks") || "").trim(),
    };
    if (!payload.alias || !payload.identity || !payload.remarks) {
      toast.error("Alias, identity, and remarks are required");
      return;
    }
    if (playerIdRaw && (!Number.isFinite(payload.player_id) || payload.player_id <= 0)) {
      toast.error("Invalid player ID");
      return;
    }
    try {
      await createBlacklistEntry(payload);
      toast.success("Blacklist entry created");
      formElement?.reset?.();
      await refreshEntries();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to create blacklist entry"));
    }
  }

  async function handleUpdateEntry() {
    if (!selectedEntryId) {
      toast.error("Select an entry first");
      return;
    }
    try {
      await updateBlacklistEntry(Number(selectedEntryId), {
        blacklist_level: Number(updateLevel || 1),
        alias: updateAlias.trim() || null,
        serial: updateSerial.trim() || null,
        roots: updateRoots.trim().toUpperCase() || null,
        remarks: updateRemarks.trim() || null,
      });
      toast.success("Blacklist entry updated");
      await refreshEntries();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to update blacklist entry"));
    }
  }

  async function handleRemoveEntry() {
    if (!selectedEntryId) {
      toast.error("Select an entry first");
      return;
    }
    try {
      await removeBlacklistEntry(Number(selectedEntryId), {
        reason: removalReason.trim() || null,
      });
      toast.success("Blacklist entry removed");
      setRemovalReason("");
      await refreshEntries();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to remove blacklist entry"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="danger" variant="flat">
                Restricted List
              </Chip>
              <Chip variant="flat" startContent={<Ban size={13} />}>
                Blacklist operations
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Blacklist Management</h2>
          </div>
          {canRead ? (
            <Button
              variant="ghost"
              startContent={<RefreshCw size={15} />}
              onPress={() => refreshEntries()}
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
                <label className="text-sm text-white/80">Status filter</label>
                <FormSelect
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  className="rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                >
                  <option value="">All</option>
                  <option value="active">active</option>
                  <option value="removed">removed</option>
                </FormSelect>
              </div>
            </Card>
          ) : null}

          {canRead ? (
            <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
              <div className="mb-2 flex items-center justify-between px-2 py-1">
                <p className="text-sm text-white/70">
                  Entries: <span className="font-semibold text-white">{entries?.length || 0}</span>
                </p>
                {entriesLoading ? <p className="text-xs text-white/55">Loading...</p> : null}
              </div>
              <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
                {(entries || []).map((entry) => {
                  const active = String(entry.id) === String(selectedEntryId);
                  return (
                    <button
                      key={entry.id}
                      type="button"
                      onClick={() => {
                        setSelectedEntryId(String(entry.id));
                        setUpdateLevel(String(entry.blacklist_level || 1));
                        setUpdateAlias(String(entry.alias || ""));
                        setUpdateSerial(String(entry.serial || ""));
                        setUpdateRoots(String(entry.roots || ""));
                        setUpdateRemarks(String(entry.remarks || ""));
                      }}
                      className={[
                        "w-full rounded-xl border p-3 text-left transition",
                        active
                          ? "border-amber-300/45 bg-amber-300/15"
                          : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                      ].join(" ")}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-white">
                          {entry.blacklist_player_id} · {entry.alias}
                        </p>
                        <Chip size="sm" color={statusChipColor(entry.status)} variant="flat">
                          {entry.status}
                        </Chip>
                      </div>
                      <p className="mt-1 text-xs text-white/65">
                        Identity: {entry.identity} · Level: {entry.blacklist_level} · Roots:{" "}
                        {entry.roots || "-"}
                      </p>
                      <p className="mt-1 text-xs text-white/70 line-clamp-2">{entry.remarks}</p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                        Created {dayjs(entry.created_at).format("YYYY-MM-DD HH:mm")}
                      </p>
                    </button>
                  );
                })}
                {!entriesLoading && (entries || []).length === 0 ? (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                    No blacklist entries found.
                  </div>
                ) : null}
              </div>
            </Card>
          ) : (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>Read access is restricted. You can still execute write actions if authorized.</p>
              </div>
            </Card>
          )}

          {entriesError ? (
            <Card className="border border-rose-300/25 bg-rose-300/10 p-3">
              <p className="text-sm text-rose-100">
                {extractApiErrorMessage(entriesError, "Failed to load blacklist entries")}
              </p>
            </Card>
          ) : null}
        </section>

        <section className="space-y-4">
          {canAdd ? (
            <FormSectionDisclosure title="Add Blacklist Entry" defaultExpanded>
              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Add Blacklist Entry</p>
              <form className="space-y-3" onSubmit={handleCreateEntry}>
                <FormInput
                  name="playerId"
                  type="number"
                  min={1}
                  placeholder="Player ID (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="level"
                  type="number"
                  min={1}
                  max={99}
                  defaultValue={1}
                  placeholder="Blacklist level"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="alias"
                  placeholder="Alias (in-game name)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="identity"
                  placeholder="Identity (account name)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="serial"
                  placeholder="Serial"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="roots"
                  maxLength={2}
                  placeholder="Roots country code"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white uppercase"
                />
                <FormTextarea
                  name="remarks"
                  rows={3}
                  placeholder="Remarks / reason"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button type="submit" color="warning" startContent={<Plus size={14} />}>
                  Add Entry
                </Button>
              </form>
            </Card>
            </FormSectionDisclosure>
          ) : null}

          {selectedEntry && canUpdate ? (
            <FormSectionDisclosure title="Update Blacklist Entry">
              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Update Entry #{selectedEntry.blacklist_player_id}</p>
              <div className="space-y-3">
                <FormInput
                  type="number"
                  min={1}
                  max={99}
                  value={updateLevel}
                  onChange={(event) => setUpdateLevel(event.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  value={updateAlias}
                  onChange={(event) => setUpdateAlias(event.target.value)}
                  placeholder="Alias"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  value={updateSerial}
                  onChange={(event) => setUpdateSerial(event.target.value)}
                  placeholder="Serial"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  maxLength={2}
                  value={updateRoots}
                  onChange={(event) => setUpdateRoots(event.target.value)}
                  placeholder="Roots"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white uppercase"
                />
                <FormTextarea
                  rows={3}
                  value={updateRemarks}
                  onChange={(event) => setUpdateRemarks(event.target.value)}
                  placeholder="Remarks"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button color="warning" onPress={handleUpdateEntry}>
                  Save Changes
                </Button>
              </div>
            </Card>
            </FormSectionDisclosure>
          ) : null}

          {selectedEntry && canRemove ? (
            <FormSectionDisclosure title="Remove Blacklist Entry">
              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Remove Entry</p>
              <FormTextarea
                rows={3}
                value={removalReason}
                onChange={(event) => setRemovalReason(event.target.value)}
                placeholder="Removal reason (optional)"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <Button
                className="mt-3"
                color="danger"
                variant="flat"
                startContent={<CircleX size={14} />}
                onPress={handleRemoveEntry}
              >
                Remove from Blacklist
              </Button>
            </Card>
            </FormSectionDisclosure>
          ) : null}

          {!canAdd && !canUpdate && !canRemove ? (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>You currently have read-only blacklist access.</p>
              </div>
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
