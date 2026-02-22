import {
  AlertDialog,
  Autocomplete,
  Button,
  Card,
  Chip,
  EmptyState,
  Header,
  Label,
  ListBox,
  SearchField,
  Separator,
  useFilter,
} from "@heroui/react";
import { CheckCheck, RefreshCw, Save, ShieldAlert } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasPermissionSet } from "../../../core/permissions/guards.js";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { ListPaginationBar } from "../../../shared/ui/ListPaginationBar.jsx";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../../shared/ui/StateBlocks.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
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

function sortUniquePermissions(values) {
  return [...new Set((values || []).map((item) => String(item).trim()).filter(Boolean))].sort();
}

function permissionListsEqual(left, right) {
  const leftSorted = sortUniquePermissions(left);
  const rightSorted = sortUniquePermissions(right);
  if (leftSorted.length !== rightSorted.length) {
    return false;
  }
  return leftSorted.every((value, index) => value === rightSorted[index]);
}

function formatSectionLabel(sectionKey) {
  if (!sectionKey) return "General";
  return String(sectionKey)
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function groupPermissionKeys(permissionKeys) {
  const grouped = new Map();

  for (const permissionKey of permissionKeys || []) {
    const normalized = String(permissionKey).trim();
    if (!normalized) continue;

    const [sectionKey] = normalized.split(".");
    const bucketKey = (sectionKey || "general").toLowerCase();
    if (!grouped.has(bucketKey)) {
      grouped.set(bucketKey, []);
    }
    grouped.get(bucketKey).push(normalized);
  }

  return [...grouped.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([sectionKey, values]) => ({
      key: sectionKey,
      label: formatSectionLabel(sectionKey),
      items: sortUniquePermissions(values),
    }));
}

export function RoleMatrixPage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);
  const { contains } = useFilter({ sensitivity: "base" });

  const canRead = hasPermissionSet(["discord_role_permissions.read"], permissions, isOwner);
  const canWrite = hasPermissionSet(["discord_role_permissions.write"], permissions, isOwner);

  const [selectedRoleId, setSelectedRoleId] = useState("");
  const [draftPermissions, setDraftPermissions] = useState([]);
  const [pendingRoleSwitch, setPendingRoleSwitch] = useState(null);
  const [isUnsavedDialogOpen, setIsUnsavedDialogOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const {
    data: roleMatrix,
    error: roleMatrixError,
    isLoading: roleMatrixLoading,
    mutate: refreshRoleMatrix,
  } = useSWR(
    canRead ? ["permissions-role-matrix", page, pageSize] : null,
    () =>
      listRoleMatrix({
        limit: pageSize + 1,
        offset: (page - 1) * pageSize,
      }),
  );

  const roleRows = useMemo(() => toArray(roleMatrix), [roleMatrix]);
  const pageRoleRows = useMemo(() => roleRows.slice(0, pageSize), [roleRows, pageSize]);
  const hasNextPage = roleRows.length > pageSize;

  const selectedRole = useMemo(
    () => pageRoleRows.find((role) => String(role.discord_role_id) === String(selectedRoleId)) || null,
    [pageRoleRows, selectedRoleId],
  );

  const selectedAssignedPermissions = useMemo(
    () => sortUniquePermissions(selectedRole?.assigned_permissions || []),
    [selectedRole?.assigned_permissions],
  );

  const isDraftDirty = useMemo(
    () => !permissionListsEqual(draftPermissions, selectedAssignedPermissions),
    [draftPermissions, selectedAssignedPermissions],
  );

  const allPermissionKeys = useMemo(
    () => sortUniquePermissions(selectedRole?.available_permissions || []),
    [selectedRole?.available_permissions],
  );

  const groupedPermissions = useMemo(
    () => groupPermissionKeys(allPermissionKeys),
    [allPermissionKeys],
  );

  if (!canRead) {
    return (
      <ForbiddenState
        title="Role Matrix Access Restricted"
        description="You need discord_role_permissions.read permission to access role matrix."
      />
    );
  }

  function ensureDraftInitialized(role) {
    const assigned = sortUniquePermissions(role?.assigned_permissions || []);
    setDraftPermissions(assigned);
  }

  function selectRole(role) {
    setSelectedRoleId(String(role.discord_role_id));
    ensureDraftInitialized(role);
    setPendingRoleSwitch(null);
  }

  function attemptRoleSwitch(role) {
    if (!selectedRole || String(role.discord_role_id) === String(selectedRole.discord_role_id)) {
      selectRole(role);
      return;
    }

    if (isDraftDirty) {
      setPendingRoleSwitch(role);
      setIsUnsavedDialogOpen(true);
      return;
    }

    selectRole(role);
  }

  function handlePermissionSelectionChange(selectionKeys) {
    const nextPermissions = normalizeSelectionToArray(selectionKeys, allPermissionKeys);
    setDraftPermissions(sortUniquePermissions(nextPermissions));
  }

  async function handleSavePermissions() {
    if (!selectedRole) {
      toast.error("Select a role first");
      return;
    }
    try {
      const nextPermissions = sortUniquePermissions(draftPermissions);
      await updateRoleMatrix(selectedRole.discord_role_id, {
        permission_keys: nextPermissions,
      });
      setDraftPermissions(nextPermissions);
      toast.success("Role permissions updated");
      await refreshRoleMatrix();
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to update role permissions"));
    }
  }

  function handleUnsavedDialogOpenChange(isOpen) {
    setIsUnsavedDialogOpen(isOpen);
    if (!isOpen) {
      setPendingRoleSwitch(null);
    }
  }

  function keepEditingCurrentRole() {
    setIsUnsavedDialogOpen(false);
    setPendingRoleSwitch(null);
  }

  function discardChangesAndSwitchRole() {
    if (pendingRoleSwitch) {
      selectRole(pendingRoleSwitch);
    }
    setIsUnsavedDialogOpen(false);
  }

  return (
    <>
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
                  Roles: <span className="font-semibold text-white">{pageRoleRows.length}</span>
                </p>
              </div>
              <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
                {roleMatrixLoading ? <LoadingBlock label="Loading roles..." /> : null}
                {pageRoleRows.map((role) => {
                  const active = String(role.discord_role_id) === String(selectedRoleId);
                  return (
                    <button
                      key={role.discord_role_id}
                      type="button"
                      onClick={() => attemptRoleSwitch(role)}
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
                {!roleMatrixLoading && pageRoleRows.length === 0 ? (
                  <EmptyBlock
                    title="No roles found"
                    description="No Discord roles are currently available in the cache."
                  />
                ) : null}
              </div>
              <div className="mt-3">
                <ListPaginationBar
                  page={page}
                  pageSize={pageSize}
                  onPageChange={setPage}
                  onPageSizeChange={(nextPageSize) => {
                    setPageSize(nextPageSize);
                    setPage(1);
                  }}
                  hasNextPage={hasNextPage}
                  isLoading={roleMatrixLoading}
                  visibleCount={pageRoleRows.length}
                />
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
              <FormSectionDisclosure title="Role Permission Editor">
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="cb-title text-2xl">{selectedRole.name}</p>
                    <p className="text-xs text-white/60">Role ID {selectedRole.discord_role_id}</p>
                  </div>
                  <Chip variant="flat">Draft: {draftPermissions.length} permissions</Chip>
                </div>

                <div className="rounded-xl border border-white/10 bg-black/35 p-3">
                  <Autocomplete
                    className="w-full"
                    placeholder="Select permissions"
                    selectionMode="multiple"
                    selectedKeys={new Set(draftPermissions)}
                    isDisabled={!canWrite || !allPermissionKeys.length}
                    onSelectionChange={handlePermissionSelectionChange}
                  >
                    <Label>Permissions</Label>
                    <Autocomplete.Trigger>
                      <Autocomplete.Value />
                      <Autocomplete.ClearButton />
                      <Autocomplete.Indicator />
                    </Autocomplete.Trigger>
                    <Autocomplete.Popover>
                      <Autocomplete.Filter filter={contains}>
                        <SearchField autoFocus name="search" variant="secondary">
                          <SearchField.Group>
                            <SearchField.SearchIcon />
                            <SearchField.Input placeholder="Search permissions..." />
                            <SearchField.ClearButton />
                          </SearchField.Group>
                        </SearchField>

                        <ListBox
                          selectionMode="multiple"
                          renderEmptyState={() => <EmptyState>No results found</EmptyState>}
                        >
                          {groupedPermissions.map((section, sectionIndex) => (
                            <Fragment key={section.key}>
                              <ListBox.Section>
                                <Header>{section.label}</Header>
                                {section.items.map((permissionKey) => (
                                  <ListBox.Item
                                    key={permissionKey}
                                    id={permissionKey}
                                    textValue={permissionKey}
                                  >
                                    {permissionKey}
                                    <ListBox.ItemIndicator />
                                  </ListBox.Item>
                                ))}
                              </ListBox.Section>
                              {sectionIndex < groupedPermissions.length - 1 ? <Separator /> : null}
                            </Fragment>
                          ))}
                        </ListBox>
                      </Autocomplete.Filter>
                    </Autocomplete.Popover>
                  </Autocomplete>

                  {allPermissionKeys.length === 0 ? (
                    <div className="mt-3">
                      <EmptyBlock
                        title="No permissions available"
                        description="This role currently has no assignable permissions."
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
            </FormSectionDisclosure>
            ) : (
              <EmptyBlock
                title="Select a role"
                description="Choose a role from the left list to review and edit permission bundles."
              />
            )}
          </section>
        </div>
      </div>

      <AlertDialog isOpen={isUnsavedDialogOpen} onOpenChange={handleUnsavedDialogOpenChange}>
        <AlertDialog.Trigger>
          <span className="hidden" />
        </AlertDialog.Trigger>
        <AlertDialog.Backdrop>
          <AlertDialog.Container>
            <AlertDialog.Dialog className="sm:max-w-[420px]">
              <AlertDialog.CloseTrigger />
              <AlertDialog.Header>
                <AlertDialog.Icon status="warning" />
                <AlertDialog.Heading>Discard unsaved changes?</AlertDialog.Heading>
              </AlertDialog.Header>
              <AlertDialog.Body>
                <p>
                  You changed permission selections for the current role and did not save yet. If you
                  switch now, those changes will be lost.
                </p>
              </AlertDialog.Body>
              <AlertDialog.Footer>
                <Button slot="close" variant="tertiary" onPress={keepEditingCurrentRole}>
                  Keep Editing
                </Button>
                <Button slot="close" variant="primary" onPress={discardChangesAndSwitchRole}>
                  Discard and Switch
                </Button>
              </AlertDialog.Footer>
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      </AlertDialog>
    </>
  );
}
