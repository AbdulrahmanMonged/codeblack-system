import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import { ExternalLink, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import useSWR from "swr";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { FormSelect } from "../../../shared/ui/FormControls.jsx";
import { FormSectionDisclosure } from "../../../shared/ui/FormSectionDisclosure.jsx";
import { ListPaginationBar } from "../../../shared/ui/ListPaginationBar.jsx";
import { EmptyBlock, ErrorBlock, LoadingBlock } from "../../../shared/ui/StateBlocks.jsx";
import { listMyOrders } from "../api/orders-api.js";

const STATUS_OPTIONS = [
  { value: "", label: "All statuses" },
  { value: "submitted", label: "Submitted" },
  { value: "accepted", label: "Accepted" },
  { value: "denied", label: "Denied" },
];

function statusColor(status) {
  const value = String(status || "").toLowerCase();
  if (value === "accepted") return "success";
  if (value === "denied") return "danger";
  return "warning";
}

export function MyOrdersPanel({ canOpenDetails }) {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const {
    data,
    error,
    isLoading,
    mutate: refresh,
  } = useSWR(["orders-mine", statusFilter, page, pageSize], ([, status, currentPage, currentPageSize]) =>
    listMyOrders({
      status: status || null,
      limit: currentPageSize + 1,
      offset: (currentPage - 1) * currentPageSize,
    }),
  );

  const rows = useMemo(() => (Array.isArray(data) ? data : []), [data]);
  const visibleRows = useMemo(() => rows.slice(0, pageSize), [rows, pageSize]);
  const hasNextPage = rows.length > pageSize;

  return (
    <FormSectionDisclosure title="My Orders Status">
      <Card className="border border-white/15 bg-black/45 p-4 shadow-2xl backdrop-blur-xl">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <FormSelect
            fieldClassName="min-w-[220px]"
            label="Filter by status"
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(String(event?.target?.value || ""));
              setPage(1);
            }}
          >
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </FormSelect>
          <Button
            variant="ghost"
            startContent={<RefreshCw size={14} />}
            isDisabled={isLoading}
            onPress={() => refresh()}
          >
            Refresh
          </Button>
        </div>

        {isLoading ? <LoadingBlock label="Loading your orders..." /> : null}
        {error ? (
          <ErrorBlock
            title="Failed to load orders"
            description={extractApiErrorMessage(error)}
            onRetry={() => refresh()}
          />
        ) : null}

        {!isLoading && !error && !visibleRows.length ? (
          <EmptyBlock
            title="No orders yet"
            description="Orders you create will appear here with their latest status."
          />
        ) : null}

        {!isLoading && !error && visibleRows.length ? (
          <div className="space-y-2">
            {visibleRows.map((order) => (
              <div
                key={order.public_id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2"
              >
                <div className="space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-white">{order.public_id}</p>
                    <Chip color={statusColor(order.status)} size="sm" variant="flat">
                      {order.status}
                    </Chip>
                  </div>
                  <p className="text-xs text-white/65">
                    Submitted {dayjs(order.submitted_at).format("YYYY-MM-DD HH:mm")} · Updated{" "}
                    {dayjs(order.updated_at).format("YYYY-MM-DD HH:mm")}
                  </p>
                </div>

                {canOpenDetails ? (
                  <Button
                    as={Link}
                    to={`/orders/${order.public_id}`}
                    size="sm"
                    variant="ghost"
                    endContent={<ExternalLink size={13} />}
                  >
                    Open
                  </Button>
                ) : null}
              </div>
            ))}
          </div>
        ) : null}

        <ListPaginationBar
          page={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(nextSize) => {
            setPageSize(nextSize);
            setPage(1);
          }}
          hasNextPage={hasNextPage}
          isLoading={isLoading}
          visibleCount={visibleRows.length}
        />
      </Card>
    </FormSectionDisclosure>
  );
}
