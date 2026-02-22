import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import {
  CheckCircle2,
  Eye,
  RefreshCw,
  RotateCcw,
  Save,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useMemo, useState } from "react";
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
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../../shared/ui/StateBlocks.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import { toArray } from "../../../shared/utils/collections.js";
import { includesSearchQuery } from "../../../shared/utils/search.js";
import {
  approveConfigChange,
  listConfigChangesAdvanced,
  listConfigRegistry,
  previewConfigRegistryKey,
  rollbackConfigRegistryKey,
  upsertConfigRegistryKey,
} from "../api/config-registry-api.js";

function statusChipColor(status) {
  const value = String(status || "").toLowerCase();
  if (value === "applied") return "success";
  if (value === "pending_approval") return "warning";
  if (value === "rejected") return "danger";
  return "default";
}

export function ConfigRegistryPage() {
  const currentUser = useAppSelector(selectCurrentUser);
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["config_registry.read"], permissions, isOwner);
  const canWrite = hasPermissionSet(["config_registry.write"], permissions, isOwner);
  const canPreview = hasPermissionSet(["config_registry.preview"], permissions, isOwner);
  const canRollback = hasPermissionSet(["config_registry.rollback"], permissions, isOwner);
  const canApprove = hasPermissionSet(["config_change.approve"], permissions, isOwner);
  const canAccess = hasAnyPermissionSet(
    [
      "config_registry.read",
      "config_registry.write",
      "config_registry.preview",
      "config_registry.rollback",
      "config_change.approve",
    ],
    permissions,
    isOwner,
  );

  const [includeSensitive, setIncludeSensitive] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [editorKey, setEditorKey] = useState("");
  const [editorValueRaw, setEditorValueRaw] = useState("{}");
  const [editorSchemaVersion, setEditorSchemaVersion] = useState("1");
  const [editorIsSensitive, setEditorIsSensitive] = useState(false);
  const [editorReason, setEditorReason] = useState("Updated from dashboard");
  const [previewResult, setPreviewResult] = useState(null);
  const [approvalReason, setApprovalReason] = useState("Approved by reviewer");
  const [rollbackReason, setRollbackReason] = useState("Rollback requested");

  const effectiveSensitiveFlag = isOwner && includeSensitive;

  const {
    data: entries,
    error: entriesError,
    isLoading: entriesLoading,
    mutate: refreshEntries,
  } = useSWR(
    canRead ? ["config-registry-entries", effectiveSensitiveFlag ? "sensitive" : "masked"] : null,
    () => listConfigRegistry({ includeSensitive: effectiveSensitiveFlag }),
  );

  const {
    data: changes,
    error: changesError,
    isLoading: changesLoading,
    mutate: refreshChanges,
  } = useSWR(
    canRead ? ["config-registry-changes", effectiveSensitiveFlag ? "sensitive" : "masked"] : null,
    () =>
      listConfigChangesAdvanced({
        limit: 120,
        includeSensitiveValues: effectiveSensitiveFlag,
      }),
  );

  const entryRows = useMemo(() => toArray(entries), [entries]);
  const changeRows = useMemo(() => toArray(changes), [changes]);

  const filteredEntryRows = useMemo(
    () =>
      entryRows.filter((entry) =>
        includesSearchQuery(entry, searchQuery, [
          "key",
          "schema_version",
          "is_sensitive",
          "updated_at",
        ]),
      ),
    [entryRows, searchQuery],
  );

  const filteredChangeRows = useMemo(
    () =>
      changeRows.filter((change) =>
        includesSearchQuery(change, searchQuery, [
          "id",
          "config_key",
          "status",
          "changed_by_user_id",
          "change_reason",
          "created_at",
        ]),
      ),
    [changeRows, searchQuery],
  );

  const pendingChanges = useMemo(
    () => filteredChangeRows.filter((change) => change.status === "pending_approval"),
    [filteredChangeRows],
  );

  if (!canAccess) {
    return (
      <ForbiddenState
        title="Configuration Registry Access Restricted"
        description="You need config registry permissions to access this page."
      />
    );
  }

  function parseEditorValue() {
    const raw = String(editorValueRaw || "").trim();
    if (!raw) {
      throw new Error("Value JSON is required");
    }
    try {
      return JSON.parse(raw);
    } catch {
      throw new Error("Value JSON must be valid JSON");
    }
  }

  async function handlePreview() {
    if (!editorKey.trim()) {
      toast.error("Key is required");
      return;
    }
    let valueJson;
    try {
      valueJson = parseEditorValue();
    } catch (error) {
      toast.error(error.message);
      return;
    }
    try {
      const preview = await previewConfigRegistryKey(editorKey.trim(), {
        value_json: valueJson,
        schema_version: Number(editorSchemaVersion || 1),
        is_sensitive: editorIsSensitive,
      });
      setPreviewResult(preview);
      toast.success(preview.valid ? "Preview valid" : "Preview has issues");
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Preview failed"));
    }
  }

  async function handleUpsert() {
    if (!editorKey.trim()) {
      toast.error("Key is required");
      return;
    }
    let valueJson;
    try {
      valueJson = parseEditorValue();
    } catch (error) {
      toast.error(error.message);
      return;
    }
    if (!editorReason.trim() || editorReason.trim().length < 3) {
      toast.error("Change reason is required (min 3 chars)");
      return;
    }
    try {
      const result = await upsertConfigRegistryKey(editorKey.trim(), {
        value_json: valueJson,
        schema_version: Number(editorSchemaVersion || 1),
        is_sensitive: editorIsSensitive,
        change_reason: editorReason.trim(),
      });
      toast.success(result.message || "Config key updated");
      await Promise.all([refreshEntries(), refreshChanges()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to apply config change"));
    }
  }

  async function handleApproveChange(changeId) {
    if (!approvalReason.trim() || approvalReason.trim().length < 3) {
      toast.error("Approval reason is required (min 3 chars)");
      return;
    }
    try {
      await approveConfigChange(changeId, {
        change_reason: approvalReason.trim(),
      });
      toast.success(`Config change #${changeId} approved`);
      await Promise.all([refreshEntries(), refreshChanges()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to approve config change"));
    }
  }

  async function handleRollback(change) {
    if (!rollbackReason.trim() || rollbackReason.trim().length < 3) {
      toast.error("Rollback reason is required (min 3 chars)");
      return;
    }
    try {
      await rollbackConfigRegistryKey(change.config_key, {
        change_id: change.id,
        change_reason: rollbackReason.trim(),
      });
      toast.success(`Rollback submitted for ${change.config_key}`);
      await Promise.all([refreshEntries(), refreshChanges()]);
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Rollback failed"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Governance
              </Chip>
              <Chip variant="flat">Config registry</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Configuration Registry</h2>
          </div>
          {canRead ? (
            <Button
              variant="ghost"
              startContent={<RefreshCw size={15} />}
              onPress={() => Promise.all([refreshEntries(), refreshChanges()])}
            >
              Refresh
            </Button>
          ) : null}
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.2fr_1fr]">
        <section className="space-y-4">
          {canRead ? (
            <>
              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
                <div className="space-y-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <label className="inline-flex items-center gap-2 text-sm text-white/80">
                      <FormInput
                        type="checkbox"
                        checked={includeSensitive}
                        disabled={!isOwner}
                        onChange={(event) => setIncludeSensitive(event.target.checked)}
                      />
                      Include sensitive values (owner only)
                    </label>
                    {!isOwner ? (
                      <Chip size="sm" variant="flat">
                        masked mode
                      </Chip>
                    ) : null}
                  </div>
                  <DashboardSearchField
                    label="Search Config Registry"
                    description="Search by config key, change ID, status, reason, or schema version."
                    placeholder="Search config entries and changes..."
                    value={searchQuery}
                    onChange={setSearchQuery}
                    className="w-full"
                    inputClassName="w-full"
                  />
                </div>
              </Card>

              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
                <p className="mb-3 cb-title text-xl">Registry Entries</p>
                <div className="max-h-[35vh] space-y-2 overflow-y-auto pr-1">
                  {entriesLoading ? <LoadingBlock label="Loading registry entries..." /> : null}
                  {filteredEntryRows.map((entry) => (
                    <button
                      key={entry.key}
                      type="button"
                      onClick={() => {
                        setEditorKey(entry.key);
                        setEditorValueRaw(JSON.stringify(entry.value_json, null, 2));
                        setEditorSchemaVersion(String(entry.schema_version || 1));
                        setEditorIsSensitive(Boolean(entry.is_sensitive));
                      }}
                      className="w-full rounded-xl border border-white/10 bg-white/5 p-3 text-left hover:bg-white/10"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-semibold text-white">{entry.key}</p>
                        <Chip size="sm" variant="flat">
                          v{entry.schema_version}
                        </Chip>
                      </div>
                      <p className="mt-1 text-xs text-white/60">
                        {entry.is_sensitive ? "sensitive" : "non-sensitive"} · updated{" "}
                        {dayjs(entry.updated_at).format("YYYY-MM-DD HH:mm")}
                      </p>
                    </button>
                  ))}
                  {!entriesLoading && filteredEntryRows.length === 0 ? (
                    <EmptyBlock
                      title="No config entries found"
                      description="No configuration keys are currently available."
                    />
                  ) : null}
                </div>
              </Card>

              <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
                <div className="mb-3 flex items-center justify-between gap-2">
                  <p className="cb-title text-xl">Recent Changes</p>
                  <Chip variant="flat">Pending {pendingChanges.length}</Chip>
                </div>
                <div className="max-h-[45vh] space-y-2 overflow-y-auto pr-1">
                  {changesLoading ? <LoadingBlock label="Loading config changes..." /> : null}
                  {filteredChangeRows.map((change) => (
                    <div
                      key={change.id}
                      className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/80"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-semibold text-white">
                          #{change.id} · {change.config_key}
                        </p>
                        <Chip size="sm" color={statusChipColor(change.status)} variant="flat">
                          {change.status}
                        </Chip>
                      </div>
                      <p className="mt-1 text-xs text-white/60">
                        {change.requires_approval ? "requires approval" : "direct apply"} · created{" "}
                        {dayjs(change.created_at).format("YYYY-MM-DD HH:mm")}
                      </p>
                      <p className="mt-1 text-xs text-white/70">{change.change_reason}</p>
                      <div className="mt-2 flex flex-wrap gap-2">
                        {canApprove && change.status === "pending_approval" ? (
                          <Button
                            size="sm"
                            color="warning"
                            variant="flat"
                            startContent={<CheckCircle2 size={13} />}
                            isDisabled={
                              Number(change.changed_by_user_id) === Number(currentUser?.userId)
                            }
                            onPress={() => handleApproveChange(change.id)}
                          >
                            Approve
                          </Button>
                        ) : null}
                        {canRollback ? (
                          <Button
                            size="sm"
                            variant="ghost"
                            startContent={<RotateCcw size={13} />}
                            onPress={() => handleRollback(change)}
                          >
                            Rollback to Before
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  ))}
                  {!changesLoading && filteredChangeRows.length === 0 ? (
                    <EmptyBlock
                      title="No config changes found"
                      description="Change history is empty for current filters."
                    />
                  ) : null}
                </div>
              </Card>
            </>
          ) : (
            <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
              <div className="flex items-start gap-3 text-sm text-white/80">
                <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
                <p>Config registry read access is restricted.</p>
              </div>
            </Card>
          )}

          {entriesError ? (
            <ErrorBlock
              title="Failed to load registry entries"
              description={extractApiErrorMessage(entriesError)}
              onRetry={() => refreshEntries()}
            />
          ) : null}
          {changesError ? (
            <ErrorBlock
              title="Failed to load config changes"
              description={extractApiErrorMessage(changesError)}
              onRetry={() => refreshChanges()}
            />
          ) : null}
        </section>

        <section className="space-y-4">
          {(canPreview || canWrite) ? (
            <FormSectionDisclosure title="Config Editor">
              <div className="mb-3 flex items-center gap-2">
                <ShieldCheck size={15} className="text-amber-200" />
                <p className="cb-title text-xl">Editor</p>
              </div>
              <div className="space-y-3">
                <FormInput
                  value={editorKey}
                  onChange={(event) => setEditorKey(event.target.value)}
                  placeholder="Config key (e.g. vacations.max_duration_days)"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <FormTextarea
                  rows={7}
                  value={editorValueRaw}
                  onChange={(event) => setEditorValueRaw(event.target.value)}
                  placeholder="JSON value"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 font-mono text-xs text-white"
                />
                <FormInput
                  type="number"
                  min={1}
                  value={editorSchemaVersion}
                  onChange={(event) => setEditorSchemaVersion(event.target.value)}
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <label className="inline-flex items-center gap-2 text-sm text-white/80">
                  <FormInput
                    type="checkbox"
                    checked={editorIsSensitive}
                    onChange={(event) => setEditorIsSensitive(event.target.checked)}
                  />
                  Mark value as sensitive
                </label>
                <FormTextarea
                  rows={2}
                  value={editorReason}
                  onChange={(event) => setEditorReason(event.target.value)}
                  placeholder="Change reason"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
                <div className="flex flex-wrap gap-2">
                  {canPreview ? (
                    <Button
                      color="warning"
                      variant="flat"
                      startContent={<Eye size={14} />}
                      onPress={handlePreview}
                    >
                      Preview
                    </Button>
                  ) : null}
                  {canWrite ? (
                    <Button
                      color="warning"
                      startContent={<Save size={14} />}
                      onPress={handleUpsert}
                    >
                      Apply / Queue
                    </Button>
                  ) : null}
                </div>
              </div>
            </FormSectionDisclosure>
          ) : null}

          {canApprove ? (
            <FormSectionDisclosure title="Approval Note">
              <p className="mb-3 cb-title text-xl">Approval Note</p>
              <FormTextarea
                rows={3}
                value={approvalReason}
                onChange={(event) => setApprovalReason(event.target.value)}
                placeholder="Reason used when approving pending config changes"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
            </FormSectionDisclosure>
          ) : null}

          {canRollback ? (
            <FormSectionDisclosure title="Rollback Note">
              <p className="mb-3 cb-title text-xl">Rollback Note</p>
              <FormTextarea
                rows={3}
                value={rollbackReason}
                onChange={(event) => setRollbackReason(event.target.value)}
                placeholder="Reason used when rolling back a config key"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
            </FormSectionDisclosure>
          ) : null}

          {previewResult ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="mb-3 cb-title text-xl">Preview Result</p>
              <Chip color={previewResult.valid ? "success" : "danger"} variant="flat">
                {previewResult.valid ? "valid" : "invalid"}
              </Chip>
              <pre className="mt-3 max-h-64 overflow-auto rounded-xl border border-white/10 bg-white/5 p-3 text-[11px] text-white/75">
                {JSON.stringify(previewResult.normalized_value, null, 2)}
              </pre>
              {previewResult.issues?.length ? (
                <div className="mt-3 space-y-1">
                  {previewResult.issues.map((issue) => (
                    <p key={issue} className="text-xs text-rose-200">
                      - {issue}
                    </p>
                  ))}
                </div>
              ) : null}
            </Card>
          ) : null}
        </section>
      </div>
    </div>
  );
}
