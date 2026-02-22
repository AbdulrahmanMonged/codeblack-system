import { Button, Card, Chip, Spinner } from "@heroui/react";
import dayjs from "dayjs";
import { CheckCircle2, CircleX, ExternalLink, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import {
  selectIsOwner,
  selectPermissions,
} from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet, hasPermissionSet } from "../../../core/permissions/guards.js";
import { FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { formatBytes } from "../../../shared/utils/formatting.js";
import { decideOrder, getOrderByPublicId } from "../api/orders-api.js";

function statusColor(status) {
  const value = String(status || "").toLowerCase();
  if (value === "accepted") return "success";
  if (value === "denied") return "danger";
  return "warning";
}

export function OrderDetailPage() {
  const navigate = useNavigate();
  const { publicId = "" } = useParams();
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);

  const canRead = hasAnyPermissionSet(["orders.read", "orders.submit"], permissions, isOwner);
  const canReview = hasPermissionSet(["orders.review"], permissions, isOwner);
  const canAccept =
    isOwner || hasPermissionSet(["orders.decision.accept"], permissions, isOwner);
  const canDeny =
    isOwner || hasPermissionSet(["orders.decision.deny"], permissions, isOwner);

  const [reviewReason, setReviewReason] = useState("");
  const [isDeciding, setIsDeciding] = useState(false);

  const {
    data: order,
    error,
    isLoading,
    mutate: refreshOrder,
  } = useSWR(canRead && publicId ? ["order-detail", publicId] : null, ([, id]) =>
    getOrderByPublicId(id),
  );

  const canShowDecisionControls = useMemo(() => {
    if (!canReview || !order) return false;
    return String(order.status || "").toLowerCase() === "submitted";
  }, [canReview, order]);

  if (!canRead) {
    return (
      <ForbiddenState
        title="Order Details Restricted"
        description="You need orders.read or orders.submit permission to open this page."
      />
    );
  }

  async function handleDecision(decision) {
    if (!order) return;
    if (decision === "denied" && !reviewReason.trim()) {
      toast.error("Reason is required when denying an order.");
      return;
    }

    setIsDeciding(true);
    try {
      await decideOrder(order.public_id, {
        decision,
        reason: reviewReason.trim() || null,
      });
      toast.success(`Order ${decision}.`);
      await refreshOrder();
    } catch (requestError) {
      toast.error(extractApiErrorMessage(requestError, "Failed to submit order decision"));
    } finally {
      setIsDeciding(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5">
      <Card className="border border-white/15 bg-black/55 px-6 py-5 shadow-2xl backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Chip color="warning" variant="flat">
                Order Detail
              </Chip>
              <Chip color={statusColor(order?.status)} variant="flat">
                {order?.status || "-"}
              </Chip>
            </div>
            <h2 className="cb-feature-title mt-3 text-4xl">{publicId || "Order"}</h2>
          </div>
          <Button variant="ghost" onPress={() => navigate("/orders")}>Back to Orders</Button>
        </div>
      </Card>

      <Card className="border border-white/15 bg-black/45 p-5 shadow-2xl backdrop-blur-xl">
        {isLoading ? <p className="text-sm text-white/70">Loading order details...</p> : null}
        {error ? (
          <p className="text-sm text-rose-100">
            {extractApiErrorMessage(error, "Failed to load order details")}
          </p>
        ) : null}

        {order ? (
          <div className="space-y-2 text-sm text-white/85">
            <p>
              <span className="text-white/60">Public ID:</span> {order.public_id}
            </p>
            <p>
              <span className="text-white/60">Status:</span> {order.status}
            </p>
            <p>
              <span className="text-white/60">In-game name:</span> {order.ingame_name}
            </p>
            <p>
              <span className="text-white/60">Account name:</span> {order.account_name}
            </p>
            <p>
              <span className="text-white/60">Completed orders:</span> {order.completed_orders}
            </p>
            <p>
              <span className="text-white/60">Proof:</span>{" "}
              <a
                href={order.proof_file_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-amber-200 underline decoration-dotted"
              >
                Open file <ExternalLink size={12} />
              </a>
            </p>
            <p>
              <span className="text-white/60">Proof size:</span> {formatBytes(order.proof_size_bytes || 0)}
            </p>
            <p>
              <span className="text-white/60">Submitted:</span>{" "}
              {dayjs(order.submitted_at).format("YYYY-MM-DD HH:mm")}
            </p>
            <p>
              <span className="text-white/60">Updated:</span>{" "}
              {dayjs(order.updated_at).format("YYYY-MM-DD HH:mm")}
            </p>
          </div>
        ) : null}
      </Card>

      {canShowDecisionControls ? (
        <Card className="border border-white/15 bg-black/45 p-5 shadow-2xl backdrop-blur-xl">
          <p className="mb-3 cb-title text-xl">Reviewer Decision</p>
          <div className="space-y-3">
            <FormTextarea
              rows={3}
              value={reviewReason}
              onChange={(event) => setReviewReason(event.target.value)}
              placeholder="Reason (required for deny, optional for accept)"
              className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                color="success"
                isPending={isDeciding}
                isDisabled={!canAccept || isDeciding}
                onPress={() => handleDecision("accepted")}
              >
                {({ isPending }) => (
                  <>
                    {isPending ? <Spinner color="current" size="sm" /> : <CheckCircle2 size={14} />}
                    {isPending ? "Processing..." : "Accept"}
                  </>
                )}
              </Button>
              <Button
                color="danger"
                variant="flat"
                isPending={isDeciding}
                isDisabled={!canDeny || isDeciding}
                onPress={() => handleDecision("denied")}
              >
                {({ isPending }) => (
                  <>
                    {isPending ? <Spinner color="current" size="sm" /> : <CircleX size={14} />}
                    {isPending ? "Processing..." : "Deny"}
                  </>
                )}
              </Button>
            </div>
          </div>
        </Card>
      ) : null}

      {!canShowDecisionControls ? (
        <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
          <div className="flex items-start gap-3 text-sm text-white/80">
            <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
            <p>
              Decision controls are available only for submitted orders and reviewers with
              `orders.review` permission.
            </p>
          </div>
        </Card>
      ) : null}
    </div>
  );
}
