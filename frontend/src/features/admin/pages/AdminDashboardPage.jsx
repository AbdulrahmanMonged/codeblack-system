import { Button, Card, Chip, Separator, Spinner } from "@heroui/react";
import dayjs from "dayjs";
import {
  Activity,
  ClipboardCheck,
  ListChecks,
  RefreshCw,
  ShieldAlert,
  UserCheck,
  UserRoundX,
  Workflow,
} from "lucide-react";
import useSWR from "swr";
import { Link } from "react-router-dom";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { getDashboardSummary } from "../api/admin-api.js";

const summaryCards = [
  {
    key: "applications",
    title: "Applications",
    icon: ClipboardCheck,
  },
  {
    key: "orders",
    title: "Orders",
    icon: ListChecks,
  },
  {
    key: "activities",
    title: "Activities",
    icon: Activity,
  },
  {
    key: "vacations",
    title: "Vacations",
    icon: UserCheck,
  },
  {
    key: "blacklist_removal_requests",
    title: "Blacklist Removals",
    icon: UserRoundX,
  },
  {
    key: "verification_requests",
    title: "Verification Requests",
    icon: UserCheck,
  },
];

function CountCard({ title, icon, total, pending }) {
  const IconComponent = icon;
  const pendingRatio = total > 0 ? Math.round((pending / total) * 100) : 0;
  return (
    <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-white/70">{title}</p>
          <p className="cb-feature-title mt-1 text-3xl text-white">{total}</p>
        </div>
        <div className="rounded-xl border border-white/15 bg-white/5 p-2">
          <IconComponent size={16} className="text-amber-200" />
        </div>
      </div>
      <div className="mt-3 space-y-1">
        <div className="flex items-center justify-between text-xs text-white/65">
          <span>Pending</span>
          <span>{pending}</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-amber-300/80 transition-all"
            style={{ width: `${pendingRatio}%` }}
          />
        </div>
      </div>
    </Card>
  );
}

export function AdminDashboardPage() {
  const { data, error, isLoading, mutate } = useSWR(
    ["admin-dashboard-summary"],
    () => getDashboardSummary(),
  );

  if (error?.status === 403) {
    return (
      <Card className="border border-rose-300/25 bg-rose-300/10 p-6 shadow-2xl backdrop-blur-xl">
        <div className="flex items-start gap-3">
          <ShieldAlert size={18} className="mt-0.5 text-rose-100" />
          <div className="space-y-1">
            <h2 className="cb-feature-title text-3xl text-rose-100">Dashboard Access Restricted</h2>
            <p className="text-sm text-rose-100/85">
              You need <code>audit.read</code> permission to access summary metrics.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Chip color="warning" variant="flat">
                Staff Overview
              </Chip>
              <Chip variant="flat" startContent={<Workflow size={13} />}>
                Backend source of truth
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">Operational Dashboard</h2>
            <p className="mt-1 text-sm text-white/75">
              Unified counts for pending work and review workload.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="ghost"
              onPress={() => mutate()}
              isPending={isLoading}
              isDisabled={isLoading}
            >
              {({ isPending }) => (
                <>
                  {isPending ? <Spinner color="current" size="sm" /> : <RefreshCw size={15} />}
                  {isPending ? "Refreshing..." : "Refresh"}
                </>
              )}
            </Button>
            <Separator orientation="vertical" className="h-6 bg-white/20" />
            <Button as={Link} to="/admin/review-queue" color="warning">
              Open Review Queue
            </Button>
          </div>
        </div>
      </Card>

      {error ? (
        <Card className="border border-rose-300/25 bg-rose-300/10 p-4 shadow-2xl backdrop-blur-xl">
          <p className="text-sm text-rose-100">
            {extractApiErrorMessage(error, "Failed to load dashboard summary")}
          </p>
        </Card>
      ) : null}

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Card
              key={index}
              className="h-36 animate-pulse border border-white/10 bg-white/5 shadow-2xl"
            />
          ))}
        </div>
      ) : null}

      {data ? (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {summaryCards.map((item) => (
              <CountCard
                key={item.key}
                title={item.title}
                icon={item.icon}
                total={data[item.key]?.total || 0}
                pending={data[item.key]?.pending || 0}
              />
            ))}

            <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
              <p className="text-sm text-white/70">Config Pending Approval</p>
              <p className="cb-feature-title mt-1 text-3xl text-white">
                {data.config_changes_pending_approval}
              </p>
              <p className="mt-3 text-xs text-white/60">
                Two-step change approvals awaiting reviewer action.
              </p>
            </Card>
          </div>

          <Card className="border border-white/15 bg-black/45 p-5 shadow-2xl backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-sm text-white/70">Unified Pending Queue</p>
                <p className="cb-feature-title text-4xl text-white">
                  {data.review_queue_pending_total}
                </p>
              </div>
              <p className="text-xs text-white/60">
                Generated at {dayjs(data.generated_at).format("YYYY-MM-DD HH:mm:ss")}
              </p>
            </div>
          </Card>
        </>
      ) : null}
    </div>
  );
}
