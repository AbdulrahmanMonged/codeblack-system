import { zodResolver } from "@hookform/resolvers/zod";
import { Button, Card, Chip } from "@heroui/react";
import dayjs from "dayjs";
import { Clock4, SearchCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { z } from "zod";
import { extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { checkApplicationEligibility } from "../api/applications-api.js";

const eligibilitySchema = z.object({
  accountName: z.string().trim().min(2, "Account name must be at least 2 characters"),
});

export function ApplicationEligibilityPage() {
  const [result, setResult] = useState(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(eligibilitySchema),
    defaultValues: { accountName: "" },
  });

  const onSubmit = handleSubmit(async (values) => {
    try {
      const data = await checkApplicationEligibility(values.accountName);
      setResult(data);
      if (data.allowed) {
        toast.success("Account is eligible to apply");
      } else {
        toast.warning("Account is not eligible right now");
      }
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Eligibility check failed"));
    }
  });

  return (
    <div className="mx-auto w-full max-w-3xl space-y-5">
      <Card className="border border-white/15 bg-black/55 shadow-2xl backdrop-blur-xl">
        <Card.Header className="space-y-2 p-7">
          <div className="flex flex-wrap items-center gap-2">
            <Chip color="warning" variant="flat">
              Public Eligibility
            </Chip>
            <Chip variant="flat" startContent={<SearchCheck size={13} />}>
              Pre-check before apply
            </Chip>
          </div>
          <Card.Title className="cb-feature-title text-4xl">
            Application Eligibility
          </Card.Title>
          <Card.Description className="text-white/80">
            Check if an account is currently allowed to submit a recruitment application.
          </Card.Description>
        </Card.Header>
        <Card.Content className="space-y-4 px-7 pb-7">
          <div className="rounded-xl border border-amber-300/30 bg-amber-300/10 p-3 text-sm text-amber-100">
            <div className="flex items-center gap-2">
              <Sparkles size={14} />
              <span>
                This checks cooldown/permanent-block/blacklist gates from backend policy.
              </span>
            </div>
          </div>

          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-1">
              <label htmlFor="accountName" className="text-sm text-white/80">
                Account Name
              </label>
              <input
                id="accountName"
                type="text"
                autoComplete="off"
                placeholder="moamen54"
                className="w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2.5 text-sm text-white outline-none transition focus:border-amber-300/60 focus:bg-white/10"
                {...register("accountName")}
              />
              {errors.accountName ? (
                <p className="text-xs text-rose-200">{errors.accountName.message}</p>
              ) : null}
            </div>

            <div className="flex flex-wrap gap-3">
              <Button type="submit" color="warning" isLoading={isSubmitting} startContent={<SearchCheck size={15} />}>
                Check Eligibility
              </Button>
              <Button as={Link} to="/applications/new" variant="ghost">
                Open Application Form
              </Button>
            </div>
          </form>
        </Card.Content>
      </Card>

      {result ? (
        <Card className="border border-white/15 bg-black/50 shadow-2xl backdrop-blur-xl">
          <Card.Header className="flex items-center justify-between gap-3 p-6">
            <Card.Title className="cb-feature-title text-2xl">Result</Card.Title>
            <Chip color={result.allowed ? "success" : "warning"} variant="flat">
              {result.allowed ? "Allowed" : "Blocked"}
            </Chip>
          </Card.Header>
          <Card.Content className="space-y-3 px-6 pb-6">
            <p className="text-sm text-white/80">
              Status: <span className="font-semibold text-white">{result.status}</span>
            </p>
            {result.wait_until ? (
              <div className="rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80">
                <div className="flex items-center gap-2 text-white">
                  <Clock4 size={14} />
                  <span className="font-semibold">Wait until</span>
                </div>
                <p>{dayjs(result.wait_until).format("YYYY-MM-DD HH:mm")}</p>
              </div>
            ) : null}
            <p className="text-sm text-white/80">
              Permanent block:{" "}
              <span className="font-semibold text-white">
                {result.permanent_block ? "Yes" : "No"}
              </span>
            </p>
            {Array.isArray(result.reasons) && result.reasons.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {result.reasons.map((reason) => (
                  <Chip key={reason} size="sm" variant="flat">
                    {reason}
                  </Chip>
                ))}
              </div>
            ) : null}
          </Card.Content>
        </Card>
      ) : null}
    </div>
  );
}
