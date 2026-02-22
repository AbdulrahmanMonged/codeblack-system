import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import { Filter, RefreshCw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { useAppSelector } from "../../../app/store/hooks.js";
import { selectIsOwner, selectPermissions } from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasPermissionSet } from "../../../core/permissions/guards.js";
import { FormInput } from "../../../shared/ui/FormControls.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../../shared/ui/StateBlocks.jsx";
import { getAuditTimeline } from "../api/admin-api.js";

const EVENT_TYPES = [
  "applications",
  "orders",
  "activities",
  "vacations",
  "blacklist",
  "config",
  "audit",
];

export function AuditTimelinePage() {
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);
  const canRead = hasPermissionSet(["audit.read"], permissions, isOwner);

  const [search, setSearch] = useState("");
  const [actorUserId, setActorUserId] = useState("");
  const [selectedEventTypes, setSelectedEventTypes] = useState(EVENT_TYPES);

  const key = useMemo(
    () => [
      "audit-timeline",
      selectedEventTypes.join(","),
      search.trim(),
      actorUserId.trim(),
    ],
    [selectedEventTypes, search, actorUserId],
  );

  const {
    data: timeline,
    error: timelineError,
    isLoading: timelineLoading,
    mutate: refreshTimeline,
  } = useSWR(canRead ? key : null, () =>
    getAuditTimeline({
      eventTypes: selectedEventTypes,
      search: search.trim() || undefined,
      actorUserId: actorUserId.trim() ? Number(actorUserId.trim()) : undefined,
      limit: 100,
      offset: 0,
    }),
  );

  if (!canRead) {
    return (
      <ForbiddenState
        title="Audit Timeline Access Restricted"
        description="You need audit.read permission to access audit timeline."
      />
    );
  }

  function toggleEventType(type) {
    setSelectedEventTypes((previous) => {
      if (previous.includes(type)) {
        if (previous.length === 1) {
          return previous;
        }
        return previous.filter((item) => item !== type);
      }
      return [...previous, type];
    });
  }

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Audit Trail
              </Chip>
              <Chip variant="flat">{timeline?.total || 0} events</Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Audit Timeline</h2>
          </div>
          <Button
            variant="ghost"
            startContent={<RefreshCw size={15} />}
            onPress={() => refreshTimeline()}
          >
            Refresh
          </Button>
        </div>
      </Card>

      <FormSectionDisclosure title="Timeline Filters" defaultExpanded>
        <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
        <div className="grid gap-3 md:grid-cols-[1fr_auto]">
          <FormInput
            value={search}
            onChange={(event) => setSearch(String(event?.target?.value || ""))}
            placeholder="Search event type, entity, summary..."
            startContent={<Search size={14} className="text-white/40" />}
            className="w-full"
          />
          <FormInput
            value={actorUserId}
            onChange={(event) => setActorUserId(String(event?.target?.value || ""))}
            placeholder="Actor user id"
            className="w-full"
          />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          {EVENT_TYPES.map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => toggleEventType(type)}
              className={[
                "rounded-full border px-3 py-1 text-xs uppercase tracking-[0.14em] transition",
                selectedEventTypes.includes(type)
                  ? "border-amber-300/45 bg-amber-300/20 text-amber-100"
                  : "border-white/15 bg-white/5 text-white/65 hover:border-white/25 hover:text-white/85",
              ].join(" ")}
            >
              <span className="inline-flex items-center gap-1">
                <Filter size={11} />
                {type}
              </span>
            </button>
          ))}
        </div>
      </Card>
      </FormSectionDisclosure>

      <Card className="border border-white/15 bg-black/45 p-2 shadow-2xl backdrop-blur-xl">
        <div className="mb-2 flex items-center justify-between px-2 py-1">
          <p className="text-sm text-white/70">
            Timeline: <span className="font-semibold text-white">{timeline?.items?.length || 0}</span>
          </p>
        </div>
        <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
          {timelineLoading ? <LoadingBlock label="Loading audit timeline..." /> : null}
          {(timeline?.items || []).map((item, index) => (
            <div
              key={`${item.event_type}-${item.entity_id}-${index}`}
              className="rounded-xl border border-white/10 bg-white/5 p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm font-semibold text-white">
                  {item.event_type}.{item.action}
                </p>
                <Chip size="sm" variant="flat">
                  {item.entity_type}
                </Chip>
              </div>
              <p className="mt-1 text-xs text-white/65">
                Entity {item.entity_id} · Actor {item.actor_user_id ?? "system"}
              </p>
              <p className="mt-2 text-sm text-white/80">{item.summary}</p>
              {item.metadata ? (
                <pre className="mt-2 max-h-48 overflow-auto rounded-xl border border-white/10 bg-black/35 p-2 text-[11px] text-white/70">
                  {JSON.stringify(item.metadata, null, 2)}
                </pre>
              ) : null}
              <p className="mt-2 text-[11px] uppercase tracking-[0.16em] text-white/45">
                {dayjs(item.occurred_at).format("YYYY-MM-DD HH:mm:ss")}
              </p>
            </div>
          ))}
          {!timelineLoading && (timeline?.items || []).length === 0 ? (
            <EmptyBlock
              title="No audit events found"
              description="No events match your current filter configuration."
            />
          ) : null}
        </div>
      </Card>

      {timelineError ? (
        <ErrorBlock
          title="Failed to load audit timeline"
          description={extractApiErrorMessage(timelineError)}
          onRetry={() => refreshTimeline()}
        />
      ) : null}
    </div>
  );
}
