import { Button, Card, Chip } from "@heroui/react";
import { FormSelect } from "../../../shared/ui/FormControls.jsx";
import { DashboardSearchField } from "../../../shared/ui/DashboardSearchField.jsx";
import dayjs from "dayjs";
import { ExternalLink, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import { useNavigate, useParams } from "react-router-dom";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasPermissionSet } from "../../../core/permissions/guards.js";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { toArray } from "../../../shared/utils/collections.js";
import { includesSearchQuery } from "../../../shared/utils/search.js";
import { getApplicationByPublicId, listApplications } from "../api/applications-api.js";

function statusChipColor(status) {
  const value = String(status || "").toLowerCase();
  if (["accepted"].includes(value)) return "success";
  if (["submitted", "pending", "under_review"].includes(value)) return "warning";
  if (["declined", "rejected"].includes(value)) return "danger";
  return "default";
}

export function ApplicationsPage() {
  const navigate = useNavigate();
  const params = useParams();
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canReadPrivate = hasPermissionSet(["applications.read_private"], permissions, isOwner);
  const canReadPublic = hasPermissionSet(["applications.read_public"], permissions, isOwner);
  const canReadAny = canReadPrivate || canReadPublic;
  const canReview = hasPermissionSet(["applications.review"], permissions, isOwner);

  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPublicId, setSelectedPublicId] = useState(params.publicId || "");

  const {
    data: applications,
    error: listError,
    isLoading: listLoading,
    mutate: refreshList,
  } = useSWR(
    canReadAny ? ["applications-list", statusFilter || "all"] : null,
    () =>
      listApplications({
        status: statusFilter || undefined,
        limit: 100,
        offset: 0,
      }),
  );

  const rows = useMemo(() => toArray(applications), [applications]);
  const filteredRows = useMemo(
    () =>
      rows.filter((row) =>
        includesSearchQuery(row, searchQuery, [
          "public_id",
          "account_name",
          "in_game_nickname",
          "submitter_type",
          "status",
        ]),
      ),
    [rows, searchQuery],
  );
  const selectedFromList = useMemo(
    () => rows.find((row) => row.public_id === selectedPublicId) || null,
    [rows, selectedPublicId],
  );
  const {
    data: selectedFromApi,
    isLoading: detailLoading,
    error: detailError,
  } = useSWR(
    selectedPublicId && !selectedFromList ? ["application-detail", selectedPublicId] : null,
    ([, publicId]) => getApplicationByPublicId(publicId),
  );
  const selected = selectedFromList || selectedFromApi || null;

  useEffect(() => {
    if (params.publicId) {
      setSelectedPublicId(params.publicId);
      return;
    }
    if (!selectedPublicId && rows.length) {
      setSelectedPublicId(rows[0].public_id);
    }
  }, [params.publicId, rows, selectedPublicId]);

  if (!canReadAny) {
    return (
      <ForbiddenState
        title="Applications Access Restricted"
        description="You need applications.read_public or applications.read_private permission."
      />
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">Recruitment</Chip>
              <Chip variant="flat">Applications + voting context</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Applications</h2>
          </div>
          <Button variant="ghost" startContent={<RefreshCw size={15} />} onPress={() => refreshList()}>
            Refresh
          </Button>
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.1fr_1fr]">
        <section className="space-y-4">
          <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
            <div className="grid gap-3 md:grid-cols-2">
              <FormSelect
                id="applications-status-filter"
                label="Status"
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              >
                <option value="">All</option>
                <option value="submitted">submitted</option>
                <option value="accepted">accepted</option>
                <option value="declined">declined</option>
              </FormSelect>
              <DashboardSearchField
                label="Search Applications"
                description="Search by public ID, in-game nickname, account name, or status."
                placeholder="Search applications..."
                value={searchQuery}
                onChange={setSearchQuery}
                className="w-full"
                inputClassName="w-full"
              />
            </div>
            {!listLoading && filteredRows.length === 0 ? (
              <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                No applications matched the search filters.
              </div>
            ) : null}
          </Card>

          <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
            <div className="mb-2 flex items-center justify-between px-2 py-1">
              <p className="text-sm text-white/70">
                Applications: <span className="font-semibold text-white">{filteredRows.length}</span>
              </p>
              {listLoading ? <p className="text-xs text-white/55">Loading...</p> : null}
            </div>

            <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
              {filteredRows.map((row) => (
                <button
                  key={row.public_id}
                  type="button"
                  onClick={() => {
                    setSelectedPublicId(row.public_id);
                    navigate(`/applications/${row.public_id}`, { replace: true });
                  }}
                  className={[
                    "w-full rounded-xl border p-3 text-left transition",
                    row.public_id === selectedPublicId
                      ? "border-amber-300/45 bg-amber-300/15"
                      : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                  ].join(" ")}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-white">
                      {row.in_game_nickname} ({row.account_name})
                    </p>
                    <Chip size="sm" color={statusChipColor(row.status)} variant="flat">
                      {row.status}
                    </Chip>
                  </div>
                  <p className="mt-1 text-xs text-white/65">{row.public_id} · {row.submitter_type}</p>
                  <p className="mt-1 text-[11px] uppercase tracking-[0.16em] text-white/45">
                    {dayjs(row.submitted_at).format("YYYY-MM-DD HH:mm")}
                  </p>
                </button>
              ))}
            </div>
          </Card>

          {listError ? (
            <Card className="border border-rose-300/25 bg-rose-300/10 p-3">
              <p className="text-sm text-rose-100">
                {extractApiErrorMessage(listError, "Failed to load applications")}
              </p>
            </Card>
          ) : null}
        </section>

        <section className="space-y-4">
          <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
            <p className="mb-3 cb-title text-xl">Application Detail</p>
            {!selected && !detailLoading ? (
              <p className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                Select an application to inspect details.
              </p>
            ) : null}
            {detailLoading ? (
              <p className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-white/70">
                Loading details...
              </p>
            ) : null}
            {detailError ? (
              <p className="rounded-xl border border-rose-300/25 bg-rose-300/10 p-4 text-sm text-rose-100">
                {extractApiErrorMessage(detailError, "Failed to load selected application")}
              </p>
            ) : null}
            {selected ? (
              <div className="space-y-2 text-sm text-white/85">
                <p><span className="text-white/60">Public ID:</span> {selected.public_id}</p>
                <p><span className="text-white/60">Status:</span> {selected.status}</p>
                <p><span className="text-white/60">Nickname:</span> {selected.in_game_nickname}</p>
                <p><span className="text-white/60">Account:</span> {selected.account_name}</p>
                <p><span className="text-white/60">English Skill:</span> {selected.english_skill}/10</p>
                <p><span className="text-white/60">Why Join:</span> {selected.why_join}</p>
                <p><span className="text-white/60">Journey:</span> {selected.cit_journey}</p>
                <p><span className="text-white/60">Former Groups:</span> {selected.former_groups_reason}</p>
                <div className="pt-1">
                  <p className="mb-1 text-white/60">Evidence</p>
                  <div className="flex flex-wrap gap-2">
                    <a href={selected.punishlog_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-white/15 bg-white/5 px-2.5 py-1.5 text-xs text-white/85 hover:bg-white/10">
                      Punishlog <ExternalLink size={12} />
                    </a>
                    <a href={selected.stats_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-white/15 bg-white/5 px-2.5 py-1.5 text-xs text-white/85 hover:bg-white/10">
                      Stats <ExternalLink size={12} />
                    </a>
                    <a href={selected.history_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-white/15 bg-white/5 px-2.5 py-1.5 text-xs text-white/85 hover:bg-white/10">
                      History <ExternalLink size={12} />
                    </a>
                  </div>
                </div>
              </div>
            ) : null}
          </Card>

          {selected ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Voting Context</p>
              <p className="text-sm text-white/75">
                Application decisions are finalized from the voting context page.
              </p>
              <Button
                className="mt-3"
                color="warning"
                onPress={() => navigate(`/voting/application/${selected.public_id}`)}
              >
                Open Voting Context
              </Button>
              {!canReview ? (
                <p className="mt-2 text-xs text-white/55">
                  You may still vote if you have `voting.cast`, but final decision controls require reviewer permissions.
                </p>
              ) : null}
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
