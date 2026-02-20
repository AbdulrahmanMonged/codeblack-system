import { Button, Card, Chip, Label, ListBox, Select } from "@heroui/react";
import { CheckCheck, RefreshCw, Save, Search, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "sonner";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasPermissionSet } from "../../../core/permissions/guards.js";
import { FormInput } from "../../../shared/ui/FormControls.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../../shared/ui/StateBlocks.jsx";
import { toArray } from "../../../shared/utils/collections.js";
import { listRoleMatrix, updateRoleMatrix } from "../api/permissions-api.js";

function normalizeSelectionToArray(selection, fallback = []) {
  if (selection === "all") {
    return [...new Set(fallback.map((item) => String(item).trim()).filter(Boolean))].sort();
  }
  if (selection instanceof Set) {
    return [...new Set([...selection].map((item) => String(item).trim()).filter(Boolean))].sort();
  }
  if (Array.isArray(selection)) {
    return [...new Set(selection.map((item) => String(item).trim()).filter(Boolean))].sort();
  }
  if (selection === null || selection === undefined) {
    return [];
  }
  return [String(selection).trim()].filter(Boolean);
}

export function RoleMatrixPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasPermissionSet(["discord_role_permissions.read"], permissions, isOwner);
  const canWrite = hasPermissionSet(["discord_role_permissions.write"], permissions, isOwner);

  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [permissionSearch, setPermissionSearch] = useState("");
  const [draftPermissions, setDraftPermissions] = useState([]);

  const {
    data: roleMatrix,
    error: roleMatrixError,
    isLoading: roleMatrixLoading,
    mutate: refreshRoleMatrix,
  } = useSWR(canRead ? ["permissions-role-matrix"] : null, () => listRoleMatrix());

  const roleRows = useMemo(() => toArray(roleMatrix), [roleMatrix]);

  const selectedRole = useMemo(
    () => roleRows.find((role) => String(role.discord_role_id) === String(selectedRoleId)) || null,
    [roleRows, selectedRoleId],
  );

  const filteredPermissions = useMemo(() => {
    const query = permissionSearch.trim().toLowerCase();
    const source = selectedRole?.available_permissions || [];
    if (!query) {
      return source;
    }
    return source.filter((item) => String(item).toLowerCase().includes(query));
  }, [permissionSearch, selectedRole?.available_permissions]);

  if (!canRead) {
    return (
      <ForbiddenState
        title="Role Matrix Access Restricted"
        description="You need discord_role_permissions.read permission to access role matrix."
      />
    );
  }

  function ensureDraftInitialized(role) {
    const assigned = [...(role?.assigned_permissions || [])].map((item) => String(item)).sort();
    setDraftPermissions(assigned);
  }

  function handlePermissionSelectionChange(selectionKeys) {
    const visibleSelection = normalizeSelectionToArray(selectionKeys, filteredPermissions);
    setDraftPermissions((previous) => {
      const hiddenSelection = previous.filter(
        (permissionKey) => !filteredPermissions.includes(permissionKey),
      );
      return [...new Set([...hiddenSelection, ...visibleSelection])].sort();
    });
  }

  async function handleSavePermissions() {
    if (!selectedRole) {
      toast.error("Select a role first");
      return;
    }
    try {
      await updateRoleMatrix(selectedRole.discord_role_id, {
        permission_keys: [...new Set(draftPermissions)].sort(),
      });
      toast.success("Role permissions updated");
      await refreshRoleMatrix();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to update role permissions"));
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Permission Governance
              </Chip>
              <Chip variant="flat">Discord roles</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Role Matrix</h2>
          </div>
          <Button
            variant="ghost"
            startContent={<RefreshCw size={15} />}
            onPress={() => refreshRoleMatrix()}
          >
            Refresh
          </Button>
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-[1.05fr_1.35fr]">
        <section className="space-y-4">
          <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
            <div className="mb-2 flex items-center justify-between px-2 py-1">
              <p className="text-sm text-white/70">
                Roles: <span className="font-semibold text-white">{roleRows.length}</span>
              </p>
            </div>
            <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
              {roleMatrixLoading ? <LoadingBlock label="Loading roles..." /> : null}
              {roleRows.map((role) => {
                const active = String(role.discord_role_id) === String(selectedRoleId);
                return (
                  <button
                    key={role.discord_role_id}
                    type="button"
                    onClick={() => {
                      setSelectedRoleId(String(role.discord_role_id));
                      ensureDraftInitialized(role);
                    }}
                    className={[
                      "w-full rounded-xl border p-3 text-left transition",
                      active
                        ? "border-amber-300/45 bg-amber-300/15"
                        : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                    ].join(" ")}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-white">{role.name}</p>
                      <Chip size="sm" variant="flat">
                        {role.assigned_permissions.length}
                      </Chip>
                    </div>
                    <p className="mt-1 text-xs text-white/65">
                      Role ID {role.discord_role_id} · Position {role.position} ·{" "}
                      {role.is_active ? "active" : "inactive"}
                    </p>
                  </button>
                );
              })}
              {!roleMatrixLoading && roleRows.length === 0 ? (
                <EmptyBlock
                  title="No roles found"
                  description="No Discord roles are currently available in the cache."
                />
              ) : null}
            </div>
          </Card>

          {roleMatrixError ? (
            <ErrorBlock
              title="Failed to load role matrix"
              description={extractApiErrorMessage(roleMatrixError)}
              onRetry={() => refreshRoleMatrix()}
            />
          ) : null}
        </section>

        <section className="space-y-4">
          {selectedRole ? (
            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="cb-title text-2xl">{selectedRole.name}</p>
                  <p className="text-xs text-white/60">Role ID {selectedRole.discord_role_id}</p>
                </div>
                <Chip variant="flat">
                  Draft: {draftPermissions.length} permissions
                </Chip>
              </div>

              <div className="mb-3">
                <FormInput
                  value={permissionSearch}
                  onChange={(event) => setPermissionSearch(String(event?.target?.value || ""))}
                  placeholder="Filter permission keys..."
                  startContent={<Search size={14} className="text-white/45" />}
                  className="w-full"
                />
              </div>

              <div className="rounded-xl border border-white/10 bg-black/35 p-3">
                <Select
                  className="w-full"
                  placeholder="Select permissions"
                  selectionMode="multiple"
                  selectedKeys={new Set(draftPermissions)}
                  isDisabled={!canWrite || !filteredPermissions.length}
                  onSelectionChange={handlePermissionSelectionChange}
                >
                  <Label>Permissions</Label>
                  <Select.Trigger>
                    <Select.Value />
                    <Select.Indicator />
                  </Select.Trigger>
                  <Select.Popover>
                    <ListBox selectionMode="multiple">
                      {filteredPermissions.map((permissionKey) => (
                        <ListBox.Item
                          key={permissionKey}
                          id={permissionKey}
                          textValue={permissionKey}
                        >
                          {permissionKey}
                          <ListBox.ItemIndicator />
                        </ListBox.Item>
                      ))}
                    </ListBox>
                  </Select.Popover>
                </Select>

                {filteredPermissions.length === 0 ? (
                  <div className="mt-3">
                    <EmptyBlock
                      title="No permissions matched"
                      description="Try clearing the filter to see all available permissions."
                    />
                  </div>
                ) : null}
              </div>

              {canWrite ? (
                <div className="mt-4 flex flex-wrap gap-2">
                  <Button
                    color="warning"
                    startContent={<Save size={14} />}
                    onPress={handleSavePermissions}
                  >
                    Save Role Permissions
                  </Button>
                  <Button
                    variant="ghost"
                    startContent={<CheckCheck size={14} />}
                    onPress={() => ensureDraftInitialized(selectedRole)}
                  >
                    Reset Draft
                  </Button>
                </div>
              ) : (
                <div className="mt-4 flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/75">
                  <ShieldAlert size={15} className="mt-0.5 text-amber-200" />
                  <p>Read-only mode. You need discord_role_permissions.write to modify this matrix.</p>
                </div>
              )}
            </Card>
          ) : (
            <EmptyBlock
              title="Select a role"
              description="Choose a role from the left list to review and edit permission bundles."
            />
          )}
        </section>
      </div>
    </div>
  );
}
