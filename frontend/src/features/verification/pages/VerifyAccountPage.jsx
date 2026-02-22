import { Button, Card, Chip, Spinner } from "@heroui/react";
import { FormInput } from "../../../shared/ui/FormControls.jsx";
import { ShieldCheck, ShieldAlert } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { toast } from "../../../shared/ui/toast.jsx";
import { useAppSelector } from "../../../app/store/hooks.js";
import {
  selectCurrentUser,
  selectIsVerified,
  selectSessionStatus,
} from "../../../app/store/slices/sessionSlice.js";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import {
  createVerificationRequest,
  getMyVerificationRequest,
} from "../api/verification-api.js";
import { Navigate } from "react-router-dom";

function statusColor(status) {
  const value = String(status || "").toLowerCase();
  if (value === "approved") return "success";
  if (value === "denied") return "danger";
  return "warning";
}

export function VerifyAccountPage() {
  const sessionStatus = useAppSelector(selectSessionStatus);
  const isVerified = useAppSelector(selectIsVerified);
  const currentUser = useAppSelector(selectCurrentUser);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    data: currentRequest,
    mutate: refreshCurrentRequest,
    isLoading,
  } = useSWR(
    sessionStatus === "authenticated" ? ["verification-request-me"] : null,
    () => getMyVerificationRequest(),
  );

  const requestStatus = String(currentRequest?.status || "").toLowerCase();
  const isVerificationLocked =
    requestStatus === "pending" || requestStatus === "approved";

  if (sessionStatus === "anonymous") {
    return <Navigate replace to="/" />;
  }
  if (sessionStatus === "authenticated" && isVerified) {
    return <Navigate replace to="/dashboard" />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (isVerificationLocked) {
      toast.warning("Verification request is locked for your current status.");
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const payload = {
      account_name: String(form.get("accountName") || "").trim(),
      mta_serial: String(form.get("mtaSerial") || "").trim(),
      forum_url: String(form.get("forumUrl") || "").trim(),
    };
    if (!payload.account_name || !payload.mta_serial || !payload.forum_url) {
      toast.error("All fields are required.");
      return;
    }
    setIsSubmitting(true);
    try {
      await createVerificationRequest(payload);
      await refreshCurrentRequest();
      formElement?.reset?.();
      toast.success("Verification request submitted.");
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to submit verification request"));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-5">
      <Card className="border border-white/15 bg-black/55 p-6 shadow-2xl backdrop-blur-xl">
        <div className="flex items-start gap-3">
          <ShieldCheck size={18} className="mt-1 text-amber-200" />
          <div>
            <p className="cb-feature-title text-3xl">Verify Your Account</p>
            <p className="mt-1 text-sm text-white/75">
              Submit your identity details. Dashboard actions stay locked until approved.
            </p>
            <p className="mt-2 text-xs text-white/60">
              Signed in as {currentUser?.username || "member"}
            </p>
          </div>
        </div>
      </Card>

      <Card className="border border-white/15 bg-black/45 p-5 shadow-2xl backdrop-blur-xl">
        <p className="mb-3 cb-title text-xl">Submit Verification Request</p>
        {isVerificationLocked ? (
          <div className="mb-3 rounded-xl border border-amber-300/25 bg-amber-300/10 px-3 py-2 text-xs text-amber-100">
            Verification form is disabled because your latest request is{" "}
            <span className="font-semibold">{requestStatus}</span>.
          </div>
        ) : null}
        <form className="space-y-3" onSubmit={handleSubmit}>
          <FormInput
            label="Account Name"
            name="accountName"
            placeholder="Account name"
            defaultValue={currentRequest?.account_name || ""}
            isDisabled={isVerificationLocked || isSubmitting}
            className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
          />
          <FormInput
            label="MTA Serial"
            name="mtaSerial"
            placeholder="MTA serial"
            defaultValue={currentRequest?.mta_serial || ""}
            isDisabled={isVerificationLocked || isSubmitting}
            className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
          />
          <FormInput
            label="Forum URL"
            name="forumUrl"
            placeholder="Forum profile URL"
            defaultValue={currentRequest?.forum_url || ""}
            isDisabled={isVerificationLocked || isSubmitting}
            className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
          />
          <Button
            type="submit"
            color="warning"
            isPending={isSubmitting}
            isDisabled={isVerificationLocked || isSubmitting}
          >
            {({ isPending }) => (
              <>
                {isPending ? <Spinner color="current" size="sm" /> : null}
                {isPending ? "Submitting..." : "Submit Request"}
              </>
            )}
          </Button>
        </form>
      </Card>

      <Card className="border border-white/15 bg-black/45 p-5 shadow-2xl backdrop-blur-xl">
        <p className="mb-3 cb-title text-xl">Latest Request Status</p>
        {isLoading ? (
          <p className="text-sm text-white/70">Loading status...</p>
        ) : currentRequest ? (
          <div className="space-y-2 text-sm text-white/80">
            <Chip color={statusColor(currentRequest.status)} variant="flat">
              {currentRequest.status}
            </Chip>
            <p>Public ID: {currentRequest.public_id}</p>
            <p>Account: {currentRequest.account_name}</p>
            <p>Serial: {currentRequest.mta_serial}</p>
            {currentRequest.review_comment ? (
              <p>Reviewer comment: {currentRequest.review_comment}</p>
            ) : null}
          </div>
        ) : (
          <div className="flex items-start gap-2 text-sm text-white/70">
            <ShieldAlert size={15} className="mt-0.5 text-amber-200" />
            <p>No verification request found yet.</p>
          </div>
        )}
      </Card>
    </div>
  );
}
