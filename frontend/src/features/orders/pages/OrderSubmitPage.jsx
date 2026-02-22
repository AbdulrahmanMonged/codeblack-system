import { zodResolver } from "@hookform/resolvers/zod";
import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import { CheckCircle2, Link2, ShieldAlert, UploadCloud } from "lucide-react";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "../../../shared/ui/toast.jsx";
import useSWR from "swr";
import { z } from "zod";
import { useAppSelector } from "../../../app/store/hooks.js";
import {
  selectCurrentUser,
  selectIsOwner,
  selectPermissions,
} from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorCode, extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { hasAnyPermissionSet } from "../../../core/permissions/guards.js";
import { FormInput } from "../../../shared/ui/FormControls.jsx";
import { ForbiddenState } from "../../../shared/ui/ForbiddenState.jsx";
import { formatBytes } from "../../../shared/utils/formatting.js";
import { getAccountLinkByUserId, submitOrder } from "../api/orders-api.js";

const defaultValues = {
  ingameName: "",
  completedOrders: "",
  proofImage: undefined,
};

const orderSchema = z.object({
  ingameName: z.string().trim().min(2, "In-game name is required"),
  completedOrders: z.string().trim().min(1, "Completed orders field is required"),
  proofImage: z.any().optional(),
});

const MAX_PROOF_SIZE_BYTES = 10 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);

function validateProofFile(file) {
  if (!file) {
    return "Proof image is required";
  }
  if (!ALLOWED_IMAGE_TYPES.has(file.type)) {
    return "Proof image must be PNG, JPEG, or WEBP";
  }
  if (file.size > MAX_PROOF_SIZE_BYTES) {
    return `Proof image must be smaller than ${formatBytes(MAX_PROOF_SIZE_BYTES)}`;
  }
  return "";
}

export function OrderSubmitPage() {
  const currentUser = useAppSelector(selectCurrentUser);
  const permissions = useAppSelector(selectPermissions);
  const isOwner = useAppSelector(selectIsOwner);
  const [submitted, setSubmitted] = useState(null);
  const [proofError, setProofError] = useState("");

  const canSubmit = hasAnyPermissionSet(["orders.submit"], permissions, isOwner);
  const canReadAccountLink = hasAnyPermissionSet(
    ["user_account_link.read", "user_account_link.write"],
    permissions,
    isOwner,
  );

  const {
    data: accountLink,
    error: accountLinkError,
    isLoading: accountLinkLoading,
  } = useSWR(
    canReadAccountLink && currentUser?.userId
      ? ["orders-account-link", currentUser.userId]
      : null,
    ([, userId]) => getAccountLinkByUserId(userId),
  );

  const {
    register,
    control,
    reset,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(orderSchema),
    defaultValues,
  });

  const proofFile = useWatch({ control, name: "proofImage" })?.[0];
  const completedOrders = useWatch({ control, name: "completedOrders" });

  const proofRegister = register("proofImage", {
    onChange: (event) => {
      const nextFile = event?.target?.files?.[0];
      const message = nextFile ? validateProofFile(nextFile) : "";
      setProofError(message);
    },
  });

  if (!canSubmit) {
    return (
      <ForbiddenState
        title="Orders Submit Permission Missing"
        description="You need orders.submit permission to submit order proofs."
      />
    );
  }

  const onSubmit = handleSubmit(async (values) => {
    setSubmitted(null);

    const proofImage = values.proofImage?.[0];
    const proofValidation = validateProofFile(proofImage);
    setProofError(proofValidation);
    if (proofValidation) {
      toast.error(proofValidation);
      return;
    }

    const formData = new FormData();
    formData.append("ingame_name", values.ingameName);
    formData.append("completed_orders", values.completedOrders);
    formData.append("proof_image", proofImage);

    try {
      const created = await submitOrder(formData);
      setSubmitted(created);
      toast.success(`Order submitted: ${created.public_id}`);
    } catch (error) {
      const code = extractApiErrorCode(error);
      if (code === "ACCOUNT_LINK_REQUIRED" || code === "VERIFIED_ACCOUNT_LINK_REQUIRED") {
        toast.error("A verified account link is required before submitting orders.");
      } else {
        toast.error(extractApiErrorMessage(error, "Order submission failed"));
      }
    }
  });

  return (
    <div className="mx-auto w-full max-w-4xl space-y-5">
      <Card className="border border-white/15 bg-black/55 shadow-2xl backdrop-blur-xl">
        <Card.Header className="space-y-2 p-7">
          <Chip color="warning" variant="flat">
            Authorized Members
          </Chip>
          <Card.Title className="cb-feature-title text-4xl">Submit Order Proof</Card.Title>
          <Card.Description className="text-white/80">
            Account name is resolved automatically from your linked user account on backend.
          </Card.Description>
        </Card.Header>

        <Card.Content className="space-y-5 px-7 pb-7">
          <div className="rounded-xl border border-white/15 bg-white/5 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm text-white/85">
              <Link2 size={15} className="text-amber-200" />
              <span>Linked account status</span>
            </div>
            {canReadAccountLink ? (
              <>
                {accountLinkLoading ? (
                  <p className="text-sm text-white/70">Checking account link...</p>
                ) : null}
                {accountLink ? (
                  <div className="space-y-1 text-sm text-white/80">
                    <p>
                      Account: <span className="font-semibold text-white">{accountLink.account_name}</span>
                    </p>
                    <p>
                      Verified:{" "}
                      <span className="font-semibold text-white">
                        {accountLink.is_verified ? "Yes" : "No"}
                      </span>
                    </p>
                    <p>Updated: {dayjs(accountLink.updated_at).format("YYYY-MM-DD HH:mm")}</p>
                  </div>
                ) : null}
                {accountLinkError ? (
                  <p className="text-sm text-rose-200">
                    No linked account found for your user yet. Contact staff to link your account.
                  </p>
                ) : null}
              </>
            ) : (
              <p className="text-sm text-white/65">
                Account link details are restricted, but submission will still use backend-linked account
                if available.
              </p>
            )}
          </div>

          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1">
                <FormInput
                  type="text"
                  label="In-game name"
                  className="w-full"
                  {...register("ingameName")}
                />
                {errors.ingameName ? (
                  <p className="text-xs text-rose-200">{errors.ingameName.message}</p>
                ) : null}
              </div>

              <div className="space-y-1">
                <FormInput
                  type="text"
                  label="Completed orders"
                  placeholder="Order IDs or summary"
                  className="w-full"
                  {...register("completedOrders")}
                />
                <div className="flex items-center justify-between">
                  {errors.completedOrders ? (
                    <p className="text-xs text-rose-200">{errors.completedOrders.message}</p>
                  ) : (
                    <span />
                  )}
                  <p className="text-xs text-white/55">{String(completedOrders || "").length} chars</p>
                </div>
              </div>
            </div>

            <div className="space-y-1 rounded-xl border border-white/10 bg-white/5 p-3">
              <FormInput
                type="file"
                label="Proof image (required)"
                accept="image/png,image/jpeg,image/webp"
                className="w-full"
                {...proofRegister}
              />
              {proofError ? <p className="text-xs text-rose-200">{proofError}</p> : null}
              {proofFile ? (
                <div className="mt-1 flex items-center gap-2 text-xs text-emerald-100">
                  <CheckCircle2 size={13} />
                  <span className="truncate">{proofFile.name}</span>
                  <span className="text-emerald-200/85">({formatBytes(proofFile.size)})</span>
                </div>
              ) : (
                <p className="text-xs text-white/55">
                  Supported: PNG/JPEG/WEBP up to {formatBytes(MAX_PROOF_SIZE_BYTES)}.
                </p>
              )}
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                type="button"
                variant="ghost"
                onPress={() => {
                  reset(defaultValues);
                  setProofError("");
                  setSubmitted(null);
                }}
              >
                Clear form
              </Button>
              <Button
                type="submit"
                color="warning"
                isLoading={isSubmitting}
                startContent={<UploadCloud size={15} />}
              >
                Submit Order
              </Button>
            </div>
          </form>
        </Card.Content>
      </Card>

      {submitted ? (
        <Card className="border border-emerald-300/25 bg-emerald-300/10 shadow-2xl backdrop-blur-xl">
          <Card.Content className="space-y-2 px-6 py-5 text-emerald-100">
            <p className="font-semibold">Order Submitted</p>
            <p className="text-sm">
              Public ID: <code>{submitted.public_id}</code>
            </p>
            <p className="text-sm">Status: {submitted.status}</p>
            <p className="text-sm">
              Proof URL:{" "}
              <a
                href={submitted.proof_file_url}
                target="_blank"
                rel="noreferrer"
                className="underline decoration-dotted"
              >
                Open uploaded file
              </a>
            </p>
          </Card.Content>
        </Card>
      ) : null}

      <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
        <div className="flex items-start gap-3 text-sm text-white/80">
          <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
          <p>
            If you see account-link errors, ask authorized staff to bind your user ID to account name
            in the backend before submitting orders.
          </p>
        </div>
      </Card>
    </div>
  );
}
