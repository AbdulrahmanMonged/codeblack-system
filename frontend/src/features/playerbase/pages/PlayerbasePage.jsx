import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import {
  BadgeAlert,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  Users,
} from "lucide-react";
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
import { toArray } from "../../../shared/utils/collections.js";
import {
  createPlayer,
  createPunishment,
  listPlayers,
  listPunishments,
  updatePunishment,
} from "../api/playerbase-api.js";

function statusChipColor(status) {
  const value = String(status || "").toLowerCase();
  if (["active", "approved", "accepted"].includes(value)) return "success";
  if (["pending", "review", "under_review"].includes(value)) return "warning";
  if (["expired", "denied", "rejected", "inactive"].includes(value)) return "danger";
  return "default";
}

export function PlayerbasePage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canReadPlayerbase = hasPermissionSet(["playerbase.read"], permissions, isOwner);
  const canWritePlayerbase = hasPermissionSet(["playerbase.write"], permissions, isOwner);
  const canReadPunishments = hasPermissionSet(["punishments.read"], permissions, isOwner);
  const canWritePunishments = hasPermissionSet(["punishments.write"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(
    ["playerbase.read", "playerbase.write", "punishments.read", "punishments.write"],
    permissions,
    isOwner,
  );

  const [search, setSearch] = useState("");
  const [selectedPlayerId, setSelectedPlayerId] = useState("");
  const [selectedPunishmentId, setSelectedPunishmentId] = useState("");
  const [punishmentStatus, setPunishmentStatus] = useState("active");
  const [punishmentExpiresAt, setPunishmentExpiresAt] = useState("");

  const {
    data: players,
    error: playersError,
    isLoading: playersLoading,
    mutate: refreshPlayers,
  } = useSWR(canReadPlayerbase ? ["playerbase-players"] : null, () =>
    listPlayers({ limit: 100, offset: 0 }),
  );

  const playerRows = useMemo(() => toArray(players), [players]);

  const filteredPlayers = useMemo(() => {
    const rows = playerRows;
    const query = search.trim().toLowerCase();
    if (!query) {
      return rows;
    }
    return rows.filter((row) => {
      const ingameName = String(row.ingame_name || "").toLowerCase();
      const accountName = String(row.account_name || "").toLowerCase();
      const serial = String(row.mta_serial || "").toLowerCase();
      return (
        ingameName.includes(query) ||
        accountName.includes(query) ||
        serial.includes(query) ||
        String(row.id).includes(query)
      );
    });
  }, [playerRows, search]);

  const selectedPlayer = useMemo(
    () => filteredPlayers.find((row) => String(row.id) === String(selectedPlayerId)) || null,
    [filteredPlayers, selectedPlayerId],
  );

  const {
    data: punishments,
    error: punishmentsError,
    isLoading: punishmentsLoading,
    mutate: refreshPunishments,
  } = useSWR(
    selectedPlayerId && canReadPunishments
      ? ["playerbase-punishments", selectedPlayerId]
      : null,
    ([, playerId]) => listPunishments(playerId),
  );

  const punishmentRows = useMemo(() => toArray(punishments), [punishments]);

  const selectedPunishment = useMemo(
    () => punishmentRows.find((row) => String(row.id) === String(selectedPunishmentId)) || null,
    [punishmentRows, selectedPunishmentId],
  );

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Playerbase Access Restricted"
        description="You need playerbase or punishment permissions to access this page."
      />
    );
  }

  async function handleCreatePlayer(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      ingame_name: String(form.get("ingameName") || "").trim(),
      account_name: String(form.get("accountName") || "").trim(),
      mta_serial: String(form.get("serial") || "").trim() || null,
      country_code: String(form.get("countryCode") || "")
        .trim()
        .toUpperCase() || null,
    };
    if (!payload.ingame_name || !payload.account_name) {
      toast.error("In-game name and account name are required");
      return;
    }
    try {
      await createPlayer(payload);
      toast.success("Player created");
      formElement?.reset?.();
      await refreshPlayers();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to create player"));
    }
  }

  async function handleCreatePunishment(event) {
    event.preventDefault();
    if (!selectedPlayerId) {
      toast.error("Select a player first");
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const expiresAt = String(form.get("expiresAt") || "").trim();
    const payload = {
      punishment_type: String(form.get("punishmentType") || "").trim(),
      severity: Number(form.get("severity") || 1),
      reason: String(form.get("reason") || "").trim(),
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
    };
    if (!payload.punishment_type || !payload.reason) {
      toast.error("Punishment type and reason are required");
      return;
    }
    try {
      await createPunishment(Number(selectedPlayerId), payload);
      toast.success("Punishment created");
      formElement?.reset?.();
      await refreshPunishments();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to create punishment"));
    }
  }

  async function handleUpdatePunishment() {
    if (!selectedPlayerId || !selectedPunishmentId) {
      toast.error("Select a punishment first");
      return;
    }
    try {
      await updatePunishment(Number(selectedPlayerId), Number(selectedPunishmentId), {
        status: punishmentStatus,
        expires_at: punishmentExpiresAt
          ? new Date(punishmentExpiresAt).toISOString()
          : null,
      });
      toast.success("Punishment updated");
      await refreshPunishments();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to update punishment"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Player Registry
              </Chip>
              <Chip variant="flat" startContent={<Users size={13} />}>
                Playerbase + punishments
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Playerbase</h2>
          </div>
          {canReadPlayerbase ? (
            <Button
              variant="ghost"
              startContent={<RefreshCw size={15} />}
              onPress={() => refreshPlayers()}
            >
              Refresh
            </Button>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-4">
          {canReadPlayerbase ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="relative">
                <Search
                  size={14}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/40"
                />
                <FormInput
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search by ID, in-game, account, serial..."
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-9 py-2.5 text-sm text-white outline-none focus:border-amber-300/60"
                />
              </div>
            </Card>
          ) : null}

          {canReadPlayerbase ? (
            <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
              <div className="mb-2 flex items-center justify-between px-2 py-1">
                <p className="text-sm text-white/70">
                  Players: <span className="font-semibold text-white">{filteredPlayers.length}</span>
                </p>
                {playersLoading ? <p className="text-xs text-white/55">Loading...</p> : null}
              </div>
              <div className="max-h-[62vh] space-y-2 overflow-y-auto pr-1">
                {filteredPlayers.map((player) => {
                  const active = String(player.id) === String(selectedPlayerId);
                  return (
                    <button
                      key={player.id}
                      type="button"
                      onClick={() => {
                        setSelectedPlayerId(String(player.id));
                        setSelectedPunishmentId("");
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
                          {player.ingame_name} ({player.account_name})
                        </p>
                        <Chip size="sm" variant="flat">
                          ID {player.id}
                        </Chip>
                      </div>
                      <p className="mt-1 text-xs text-white/65">
                        Serial: {player.mta_serial || "-"} · Country: {player.country_code || "-"}
                      </p>
                      <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                        Updated {dayjs(player.updated_at).format("YYYY-MM-DD HH:mm")}
                      </p>
                    </button>
                  );
                })}
                {!playersLoading && filteredPlayers.length === 0 ? (
                  <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                    No players found.
                  </div>
                ) : null}
              </div>
            </Card>
          ) : (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>Player listing is restricted. You can still submit write actions if permitted.</p>
              </div>
            </Card>
          )}

          {playersError ? (
            <Card className="border border-rose-300/25 bg-rose-300/10 p-3">
              <p className="text-sm text-rose-100">
                {extractApiErrorMessage(playersError, "Failed to load players")}
              </p>
            </Card>
          ) : null}
        </section>

        <section className="space-y-4">
          
          {canWritePlayerbase ? (
            <FormSectionDisclosure title="Create Player">
              <form className="space-y-3" onSubmit={handleCreatePlayer}>
                <FormInput
                  name="ingameName"
                  placeholder="In-game name"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="accountName"
                  placeholder="Account name"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="serial"
                  placeholder="MTA serial (optional)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="countryCode"
                  maxLength={2}
                  placeholder="Country code (e.g. EG)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white uppercase"
                />
                <Button type="submit" color="warning" startContent={<Plus size={14} />}>
                  Create Player
                </Button>
                </form>
            </FormSectionDisclosure>
          ) : null}

          <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
            <p className="mb-3 cb-title text-xl">Punishments</p>

            {canReadPunishments ? (
              <>
                <p className="mb-2 text-xs text-white/60">
                  Selected player:{" "}
                  <span className="font-semibold text-white">
                    {selectedPlayer ? `${selectedPlayer.ingame_name} (#${selectedPlayer.id})` : "none"}
                  </span>
                </p>
                <div className="max-h-52 space-y-2 overflow-y-auto pr-1">
                  {punishmentRows.map((punishment) => {
                    const active = String(punishment.id) === String(selectedPunishmentId);
                    return (
                      <button
                        key={punishment.id}
                        type="button"
                        onClick={() => {
                          setSelectedPunishmentId(String(punishment.id));
                          setPunishmentStatus(String(punishment.status || "active"));
                          setPunishmentExpiresAt(
                            punishment.expires_at
                              ? dayjs(punishment.expires_at).format("YYYY-MM-DDTHH:mm")
                              : "",
                          );
                        }}
                        className={[
                          "w-full rounded-xl border p-2.5 text-left transition",
                          active
                            ? "border-amber-300/45 bg-amber-300/10"
                            : "border-white/10 bg-white/5 hover:bg-white/10",
                        ].join(" ")}
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-sm font-medium text-white">
                            {punishment.punishment_type} · severity {punishment.severity}
                          </p>
                          <Chip size="sm" color={statusChipColor(punishment.status)} variant="flat">
                            {punishment.status}
                          </Chip>
                        </div>
                        <p className="mt-1 text-xs text-white/65">{punishment.reason}</p>
                        <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                          Issued {dayjs(punishment.issued_at).format("YYYY-MM-DD HH:mm")}
                        </p>
                      </button>
                    );
                  })}
                  {!punishmentsLoading && punishmentRows.length === 0 ? (
                    <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/70">
                      No punishments found for selected player.
                    </div>
                  ) : null}
                </div>
              </>
            ) : (
              <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/75">
                <BadgeAlert size={15} className="mt-0.5 text-amber-200" />
                <p>Punishment read access is restricted.</p>
              </div>
            )}

            {punishmentsError ? (
              <p className="mt-2 text-sm text-rose-200">
                {extractApiErrorMessage(punishmentsError, "Failed to load punishments")}
              </p>
            ) : null}
          </Card>

          
          {canWritePunishments ? (
            <FormSectionDisclosure title="Create Punishment">
              <form className="space-y-3" onSubmit={handleCreatePunishment}>
                <FormInput
                  name="punishmentType"
                  placeholder="Type (e.g. warn, suspension)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="severity"
                  type="number"
                  min={1}
                  max={10}
                  defaultValue={1}
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormTextarea
                  name="reason"
                  rows={3}
                  placeholder="Reason"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormInput
                  name="expiresAt"
                  type="datetime-local"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button type="submit" variant="ghost" startContent={<Plus size={14} />}>
                  Create Punishment
                </Button>
                </form>
            </FormSectionDisclosure>
          ) : null}

          {canWritePunishments && selectedPunishment ? (
            <FormSectionDisclosure title="Update Punishment">
              <p className="mb-3 cb-title text-xl">Update Punishment #{selectedPunishment.id}</p>
              <div className="space-y-3">
                <FormSelect
                  value={punishmentStatus}
                  onChange={(event) => setPunishmentStatus(event.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                >
                  <option value="active">active</option>
                  <option value="expired">expired</option>
                  <option value="revoked">revoked</option>
                </FormSelect>
                <FormInput
                  type="datetime-local"
                  value={punishmentExpiresAt}
                  onChange={(event) => setPunishmentExpiresAt(event.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <Button color="warning" onPress={handleUpdatePunishment}>
                  Save Punishment
                </Button>
              </div>
            </FormSectionDisclosure>
          ) : null}
        </section>
      </div>
    </div>
  );
}
