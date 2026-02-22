import { Button, Card, Chip } from "@heroui/react";
import { FormInput, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import dayjs from "dayjs";
import { ArrowRight, RotateCcw, ShieldAlert } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import {
  checkBlacklistRemovalEligibility,
  submitBlacklistRemovalRequest,
} from "../api/blacklist-api.js";

function statusColor(status) {
  const value = String(status || "").toLowerCase();
  if (value === "pending") return "warning";
  if (value === "approved") return "success";
  if (["denied", "rejected"].includes(value)) return "danger";
  return "default";
}

export function BlacklistRemovalRequestPage() {
  const [step, setStep] = useState(1);
  const [accountName, setAccountName] = useState("");
  const [requestText, setRequestText] = useState("");
  const [checkResult, setCheckResult] = useState(null);
  const [submitted, setSubmitted] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function runCheck() {
    const normalized = accountName.trim().toLowerCase();
    if (normalized.length < 2) {
      toast.error("Enter a valid account name first.");
      return;
    }
    setIsChecking(true);
    try {
      const result = await checkBlacklistRemovalEligibility(normalized);
      setCheckResult(result);
      if (!result.is_blacklisted) {
        toast.error(result.status_message || "This account is not currently blacklisted.");
        return;
      }
      if (!result.can_submit) {
        toast.error(
          result.status_message ||
            "A pending removal request already exists for this account.",
        );
        return;
      }
      setAccountName(result.account_name);
      setStep(2);
      toast.success("Blacklist check passed. Continue to step 2.");
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Failed to check blacklist status"));
    } finally {
      setIsChecking(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = requestText.trim();
    if (trimmed.length < 20) {
      toast.error("Please provide a more detailed explanation (at least 20 chars).");
      return;
    }
    setIsSubmitting(true);
    try {
      const created = await submitBlacklistRemovalRequest({
        account_name: accountName,
        request_text: trimmed,
      });
      setSubmitted(created);
      toast.success(`Removal request submitted: ${created.public_id}`);
      setStep(1);
      setCheckResult(null);
      setRequestText("");
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Could not submit removal request"));
    } finally {
      setIsSubmitting(false);
    }
  }

  function resetFlow() {
    setStep(1);
    setCheckResult(null);
    setSubmitted(null);
    setRequestText("");
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-5">
      <Card className="border border-white/15 bg-black/55 shadow-2xl backdrop-blur-xl">
        <Card.Header className="space-y-2 p-7">
          <Chip variant="flat" color="warning">
            Public Request
          </Chip>
          <Card.Title className="cb-feature-title text-4xl">Blacklist Removal Request</Card.Title>
          <Card.Description className="text-white/80">
            Step 1 checks if the account is blacklisted. Step 2 lets you submit your explanation.
          </Card.Description>
        </Card.Header>
        <Card.Content className="space-y-4 px-7 pb-7">
          <div className="flex items-center gap-2 text-xs text-white/65">
            <Chip size="sm" variant={step === 1 ? "flat" : "bordered"}>1. Check</Chip>
            <ArrowRight size={12} className="text-white/45" />
            <Chip size="sm" variant={step === 2 ? "flat" : "bordered"}>2. Submit</Chip>
          </div>

          {step === 1 ? (
            <div className="space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <FormInput
                    label="Account Name"
                    value={accountName}
                    onChange={(event) => setAccountName(event.target.value)}
                    onEnter={runCheck}
                    placeholder="Account name"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                </div>
                <Button
                  color="warning"
                  className="sm:self-end"
                  onPress={runCheck}
                  isLoading={isChecking}
                >
                  Check Eligibility
                </Button>
              </div>
            </div>
          ) : (
            <form className="space-y-3" onSubmit={handleSubmit}>
              <FormInput
                label="Account Name"
                value={accountName}
                isDisabled
                placeholder="Account name"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <FormTextarea
                label="Removal Request Explanation"
                rows={6}
                value={requestText}
                onChange={(event) => setRequestText(event.target.value)}
                placeholder="Explain why blacklist removal should be considered"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  startContent={<RotateCcw size={14} />}
                  onPress={resetFlow}
                >
                  Start Over
                </Button>
                <Button type="submit" color="warning" isLoading={isSubmitting}>
                  Submit Request
                </Button>
              </div>
            </form>
          )}
        </Card.Content>
      </Card>

      {checkResult && !checkResult.is_blacklisted ? (
        <Card className="border border-rose-300/25 bg-rose-300/10 p-4">
          <p className="text-sm text-rose-100">
            {checkResult.status_message ||
              `Account ${checkResult.account_name} is not currently blacklisted.`}
          </p>
        </Card>
      ) : null}

      {checkResult?.is_blacklisted && !checkResult.can_submit ? (
        <Card className="border border-amber-300/25 bg-amber-300/10 p-4">
          <p className="text-sm text-amber-100">
            {checkResult.status_message || "Removal request is already pending."}
          </p>
        </Card>
      ) : null}

      {(checkResult?.recent_requests || []).length ? (
        <Card className="border border-white/15 bg-black/45 shadow-2xl backdrop-blur-xl">
          <Card.Header className="px-6 pt-5">
            <Card.Title className="text-lg text-white">Previous Removal Requests</Card.Title>
            <Card.Description className="text-white/70">
              Latest requests for <span className="font-medium text-white">{checkResult.account_name}</span>
            </Card.Description>
          </Card.Header>
          <Card.Content className="space-y-3 px-6 pb-6">
            {checkResult.recent_requests.map((item) => (
              <div
                key={item.public_id}
                className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/85"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium">
                    Request <code>{item.public_id}</code>
                  </p>
                  <Chip size="sm" color={statusColor(item.status)} variant="flat">
                    {item.status}
                  </Chip>
                </div>
                <p className="mt-1 text-xs text-white/60">
                  Submitted: {dayjs(item.requested_at).format("YYYY-MM-DD HH:mm")}
                </p>
                {item.reviewed_at ? (
                  <p className="mt-1 text-xs text-white/60">
                    Reviewed: {dayjs(item.reviewed_at).format("YYYY-MM-DD HH:mm")}
                  </p>
                ) : null}
                {item.review_comment ? (
                  <p className="mt-2 text-sm text-white/75">{item.review_comment}</p>
                ) : null}
              </div>
            ))}
          </Card.Content>
        </Card>
      ) : null}

      {submitted ? (
        <Card className="border border-emerald-300/25 bg-emerald-300/10 shadow-2xl backdrop-blur-xl">
          <Card.Content className="space-y-2 px-6 py-5 text-emerald-100">
            <p className="font-semibold">Request Submitted</p>
            <p className="text-sm">Public ID: <code>{submitted.public_id}</code></p>
            <p className="text-sm">Status: {submitted.status}</p>
            <p className="text-sm">
              Requested at: {dayjs(submitted.requested_at).format("YYYY-MM-DD HH:mm")}
            </p>
          </Card.Content>
        </Card>
      ) : null}

      <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
        <div className="flex items-start gap-3 text-sm text-white/80">
          <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
          <p>Approval is manual and not guaranteed.</p>
        </div>
      </Card>
    </div>
  );
}
