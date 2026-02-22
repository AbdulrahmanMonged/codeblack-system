import { Button, Card, Chip, Spinner } from "@heroui/react";
import { FormInput, FormTextarea } from "../../../shared/ui/FormControls.jsx";
import { ArrowLeft, ArrowRight, CheckCircle2, CircleX, ShieldAlert } from "lucide-react";
import dayjs from "dayjs";
import { useEffect, useMemo, useState } from "react";
import { toast } from "../../../shared/ui/toast.jsx";
import { extractApiErrorCode, extractApiErrorMessage } from "../../../core/api/error-utils.js";
import { formatBytes } from "../../../shared/utils/formatting.js";
import { checkApplicationEligibility, submitApplication } from "../api/applications-api.js";

const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const ALLOWED_IMAGE_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
const RECAPTCHA_SITE_KEY = import.meta.env.VITE_RECAPTCHA_SITE_KEY || "6LeIGHIsAAAAABAzeoZxvO-98ut_5RJRGhqOi6vi";
const RECAPTCHA_ACTION = import.meta.env.VITE_RECAPTCHA_ACTION || "application_submit";

const AGREEMENT_TEXT = `submit this application with utmost sincerity, hoping that it conveys both my respect for CODEBLACK and my readiness to embrace the challenges and responsibilities that come with joining its ranks.
This apprenticeship is an opportunity not just to learn but to contribute, to grow under the tutelage of exceptional individuals, and to forge a legacy of my own within the framework of excellence that defines CODEBLACK.
My gratitude for the consideration of this application is boundless, and I remain at your disposal should any additional information or clarifications be required.`;

function validateImage(file, label) {
  if (!file) return `${label} is required`;
  if (!ALLOWED_IMAGE_TYPES.has(file.type)) return `${label} must be PNG/JPEG/WEBP`;
  if (file.size > MAX_IMAGE_BYTES) return `${label} must be <= ${formatBytes(MAX_IMAGE_BYTES)}`;
  return "";
}

function getImageValidationState(file, label) {
  const errorMessage = validateImage(file, label);
  if (errorMessage) {
    return {
      isValid: false,
      message: errorMessage,
      fileName: file?.name || "",
      sizeLabel: file ? formatBytes(file.size) : "",
    };
  }
  return {
    isValid: true,
    message: `${label} identified successfully`,
    fileName: file?.name || "",
    sizeLabel: file ? formatBytes(file.size) : "",
  };
}

function readInputValue(valueOrEvent) {
  if (typeof valueOrEvent === "string" || typeof valueOrEvent === "number") {
    return String(valueOrEvent);
  }
  return String(valueOrEvent?.target?.value ?? "");
}

function readCheckboxValue(valueOrEvent) {
  if (typeof valueOrEvent === "boolean") {
    return valueOrEvent;
  }
  if (typeof valueOrEvent?.target?.checked === "boolean") {
    return valueOrEvent.target.checked;
  }
  if (typeof valueOrEvent?.currentTarget?.checked === "boolean") {
    return valueOrEvent.currentTarget.checked;
  }
  if (typeof valueOrEvent?.isSelected === "boolean") {
    return valueOrEvent.isSelected;
  }
  if (typeof valueOrEvent?.selected === "boolean") {
    return valueOrEvent.selected;
  }
  return false;
}

function readFileValue(valueOrEvent) {
  const files = valueOrEvent?.target?.files;
  return files?.[0] || null;
}

function loadRecaptcha() {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined") {
      reject(new Error("reCAPTCHA is unavailable in this environment"));
      return;
    }
    if (window.grecaptcha?.ready) {
      resolve(window.grecaptcha);
      return;
    }
    const existing = document.querySelector('script[data-cb-recaptcha="1"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(window.grecaptcha));
      existing.addEventListener("error", () => reject(new Error("Failed to load reCAPTCHA")));
      return;
    }
    const script = document.createElement("script");
    script.src = `https://www.google.com/recaptcha/api.js?render=${encodeURIComponent(RECAPTCHA_SITE_KEY)}`;
    script.async = true;
    script.defer = true;
    script.setAttribute("data-cb-recaptcha", "1");
    script.onload = () => resolve(window.grecaptcha);
    script.onerror = () => reject(new Error("Failed to load reCAPTCHA"));
    document.head.appendChild(script);
  });
}

async function resolveCaptchaToken() {
  const recaptcha = await loadRecaptcha();
  return new Promise((resolve, reject) => {
    recaptcha.ready(() => {
      recaptcha.execute(RECAPTCHA_SITE_KEY, { action: RECAPTCHA_ACTION }).then(resolve).catch(reject);
    });
  });
}

function historyStatusColor(status) {
  const value = String(status || "").toLowerCase();
  if (value === "accepted") return "success";
  if (value === "declined" || value === "denied" || value === "rejected") return "danger";
  return "warning";
}

export function ApplicationSubmitPage() {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCheckingEligibility, setIsCheckingEligibility] = useState(false);
  const [isCaptchaLoading, setIsCaptchaLoading] = useState(true);
  const [captchaLoadError, setCaptchaLoadError] = useState("");
  const [eligibility, setEligibility] = useState(null);
  const [submitted, setSubmitted] = useState(null);

  const [form, setForm] = useState({
    accountName: "",
    inGameNickname: "",
    mtaSerial: "",
    englishSkill: 8,
    hasSecondAccount: false,
    secondAccountName: "",
    citJourney: "",
    formerGroupsReason: "",
    whyJoin: "",
    punishlogImage: null,
    statsImage: null,
    historyImage: null,
    agreeTos: false,
    agreeLetter: false,
  });

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        await loadRecaptcha();
        if (!active) return;
        setIsCaptchaLoading(false);
        setCaptchaLoadError("");
      } catch (error) {
        if (!active) return;
        setIsCaptchaLoading(false);
        setCaptchaLoadError(
          error instanceof Error && error.message
            ? error.message
            : "Failed to load reCAPTCHA",
        );
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  async function ensureCaptchaLoaded() {
    try {
      setIsCaptchaLoading(true);
      await loadRecaptcha();
      setCaptchaLoadError("");
      return true;
    } catch (error) {
      setCaptchaLoadError(
        error instanceof Error && error.message
          ? error.message
          : "Failed to load reCAPTCHA",
      );
      return false;
    } finally {
      setIsCaptchaLoading(false);
    }
  }

  const canMoveFromStep = useMemo(() => {
    if (step === 1) {
      return Boolean(eligibility?.allowed && form.accountName.trim());
    }
    if (step === 2) {
      const inGameNickname = String(form.inGameNickname || "").trim();
      const mtaSerial = String(form.mtaSerial || "").trim();
      const englishSkill = Number(form.englishSkill);
      const secondAccountName = String(form.secondAccountName || "").trim();
      const hasSecondAccount = form.hasSecondAccount === true;
      if (inGameNickname.length < 2) return false;
      if (mtaSerial.length < 10) return false;
      if (!Number.isFinite(englishSkill) || englishSkill < 0 || englishSkill > 10) return false;
      if (hasSecondAccount && secondAccountName.length < 2) return false;
      return true;
    }
    if (step === 3) {
      return (
        form.citJourney.trim().length >= 40 &&
        form.formerGroupsReason.trim().length >= 25 &&
        form.whyJoin.trim().length >= 25
      );
    }
    if (step === 4) {
      return !validateImage(form.punishlogImage, "Punishlog image") &&
        !validateImage(form.statsImage, "Stats image") &&
        !validateImage(form.historyImage, "History image");
    }
    if (step === 5) {
      return form.agreeTos && form.agreeLetter;
    }
    return false;
  }, [eligibility, form, step]);

  async function runEligibilityCheck() {
    const normalized = form.accountName.trim().toLowerCase();
    if (normalized.length < 2) {
      toast.error("Enter a valid account name first.");
      return;
    }
    setIsCheckingEligibility(true);
    try {
      const captchaLoaded = await ensureCaptchaLoaded();
      if (!captchaLoaded) {
        toast.error("Captcha must load first. Disable blockers and try again.");
        return;
      }
      const result = await checkApplicationEligibility(normalized);
      setEligibility(result);
      if (!result.allowed) {
        toast.error(
          Array.isArray(result.reasons) && result.reasons.length
            ? result.reasons.join(" | ")
            : "This account is not currently eligible.",
        );
        return;
      }
      setForm((prev) => ({ ...prev, accountName: normalized }));
      toast.success("Eligibility check passed.");
    } catch (error) {
      toast.error(extractApiErrorMessage(error, "Eligibility check failed"));
    } finally {
      setIsCheckingEligibility(false);
    }
  }

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit() {
    if (!canMoveFromStep) {
      toast.error("Complete this step first.");
      return;
    }
    setIsSubmitting(true);
    try {
      const captchaToken = await resolveCaptchaToken();
      const hasSecondAccount = form.hasSecondAccount === true;
      const formData = new FormData();
      formData.append("account_name", form.accountName.trim().toLowerCase());
      formData.append("in_game_nickname", form.inGameNickname.trim());
      formData.append("mta_serial", form.mtaSerial.trim());
      formData.append("english_skill", String(form.englishSkill));
      formData.append("has_second_account", hasSecondAccount ? "true" : "false");
      if (hasSecondAccount && form.secondAccountName.trim()) {
        formData.append("second_account_name", form.secondAccountName.trim());
      }
      formData.append("cit_journey", form.citJourney.trim());
      formData.append("former_groups_reason", form.formerGroupsReason.trim());
      formData.append("why_join", form.whyJoin.trim());
      formData.append("punishlog_image", form.punishlogImage);
      formData.append("stats_image", form.statsImage);
      formData.append("history_image", form.historyImage);
      formData.append("captcha_token", captchaToken);

      const created = await submitApplication(formData);
      setSubmitted(created);
      toast.success(`Application submitted: ${created.public_id}`);
      setStep(1);
      setEligibility(null);
      setForm({
        accountName: "",
        inGameNickname: "",
        mtaSerial: "",
        englishSkill: 8,
        hasSecondAccount: false,
        secondAccountName: "",
        citJourney: "",
        formerGroupsReason: "",
        whyJoin: "",
        punishlogImage: null,
        statsImage: null,
        historyImage: null,
        agreeTos: false,
        agreeLetter: false,
      });
    } catch (error) {
      const code = extractApiErrorCode(error);
      if (code === "CAPTCHA_TOKEN_REQUIRED") {
        toast.error("Captcha token is required by current policy.");
      } else if (code === "CAPTCHA_SCORE_TOO_LOW") {
        toast.error("Captcha score is too low. Please try again.");
      } else {
        toast.error(extractApiErrorMessage(error, "Application submission failed"));
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function nextStep() {
    if (!canMoveFromStep) {
      toast.error("Complete this step first.");
      return;
    }
    setStep((prev) => Math.min(prev + 1, 5));
  }

  function previousStep() {
    setStep((prev) => Math.max(prev - 1, 1));
  }

  function handleFormEnter(event) {
    if (event.defaultPrevented) return;
    if (event.key !== "Enter") return;
    if (event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return;

    const tagName = String(event.target?.tagName || "").toLowerCase();
    const inputType = String(event.target?.type || "").toLowerCase();

    if (tagName === "textarea" || tagName === "button" || inputType === "file") {
      return;
    }

    event.preventDefault();

    if (step === 1 && !eligibility?.allowed) {
      if (!isCheckingEligibility && !isCaptchaLoading) {
        runEligibilityCheck();
      }
      return;
    }

    if (step < 5) {
      nextStep();
      return;
    }

    if (!isSubmitting) {
      handleSubmit();
    }
  }

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <Card className="border border-white/15 bg-black/55 shadow-2xl backdrop-blur-xl">
        <Card.Header className="space-y-3 p-7">
          <div className="flex flex-wrap items-center gap-2">
            <Chip color="warning" variant="flat">Recruitment Application</Chip>
            <Chip variant="flat">5-step workflow</Chip>
          </div>
          <Card.Title className="cb-feature-title text-4xl">Application Wizard</Card.Title>
          <Card.Description className="text-white/80">
            Complete each phase to continue. Account identity is locked after eligibility passes.
          </Card.Description>
          <div className="flex flex-wrap gap-2 text-xs text-white/70">
            {["Eligibility", "Account", "Experience", "Evidence", "Agreement"].map((label, index) => (
              <Chip key={label} size="sm" variant={step === index + 1 ? "flat" : "bordered"}>
                {index + 1}. {label}
              </Chip>
            ))}
          </div>
        </Card.Header>
        <Card.Content className="space-y-5 px-7 pb-7" onKeyDownCapture={handleFormEnter}>
          {step === 1 ? (
            <div className="space-y-3">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <div className="flex-1">
                  <FormInput
                    label="Account Name"
                    value={form.accountName}
                    onChange={(valueOrEvent) =>
                      setField("accountName", readInputValue(valueOrEvent))
                    }
                    placeholder="Account name"
                    className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                </div>
                <Button
                  color="warning"
                  className="sm:self-end"
                  onPress={runEligibilityCheck}
                  isPending={isCheckingEligibility || isCaptchaLoading}
                  isDisabled={isCheckingEligibility || isCaptchaLoading}
                >
                  {({ isPending }) => (
                    <>
                      {isPending ? <Spinner color="current" size="sm" /> : null}
                      {isPending ? "Checking..." : "Check Eligibility"}
                    </>
                  )}
                </Button>
              </div>
              <p
                className={[
                  "text-xs",
                  captchaLoadError
                    ? "text-rose-200"
                    : isCaptchaLoading
                      ? "text-amber-100"
                      : "text-emerald-100",
                ].join(" ")}
              >
                {captchaLoadError
                  ? `Captcha error: ${captchaLoadError}`
                  : isCaptchaLoading
                    ? "Loading captcha security check..."
                    : "Captcha security check is ready."}
              </p>
              {eligibility ? (
                <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/80">
                  <p>Status: {eligibility.status}</p>
                  <p>Allowed: {eligibility.allowed ? "Yes" : "No"}</p>
                  {eligibility.wait_until ? <p>Wait until: {eligibility.wait_until}</p> : null}
                  {Array.isArray(eligibility.application_history) &&
                  eligibility.application_history.length > 0 ? (
                    <div className="mt-3 space-y-2 rounded-xl border border-white/10 bg-black/35 p-3">
                      <p className="text-xs uppercase tracking-[0.16em] text-white/65">
                        Previous Applications
                      </p>
                      {eligibility.application_history.map((item) => (
                        <div
                          key={item.public_id}
                          className="rounded-lg border border-white/10 bg-white/5 px-3 py-2"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-white">{item.public_id}</p>
                            <Chip size="sm" color={historyStatusColor(item.status)} variant="flat">
                              {item.status}
                            </Chip>
                          </div>
                          <p className="mt-1 text-xs text-white/65">
                            Submitted {dayjs(item.submitted_at).format("YYYY-MM-DD HH:mm")}
                          </p>
                          {item.decision_reason &&
                          ["declined", "denied", "rejected"].includes(
                            String(item.status || "").toLowerCase(),
                          ) ? (
                            <p className="mt-1 text-xs text-rose-100">
                              Denial reason: {item.decision_reason}
                            </p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ) : null}

          {step === 2 ? (
            <div className="grid gap-3 md:grid-cols-2">
              <FormInput
                label="Account Name"
                value={form.accountName}
                isDisabled
                placeholder="Account name"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <FormInput
                label="In-Game Nickname"
                value={form.inGameNickname}
                onChange={(valueOrEvent) =>
                  setField("inGameNickname", readInputValue(valueOrEvent))
                }
                placeholder="In-game nickname"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <FormInput
                label="MTA Serial"
                value={form.mtaSerial}
                onChange={(valueOrEvent) => setField("mtaSerial", readInputValue(valueOrEvent))}
                placeholder="MTA serial"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <FormInput
                label="English Skills"
                type="number"
                min={0}
                max={10}
                value={form.englishSkill}
                onChange={(valueOrEvent) => {
                  const rawValue = readInputValue(valueOrEvent);
                  const parsed = Number(rawValue === "" ? "0" : rawValue);
                  setField("englishSkill", Number.isFinite(parsed) ? parsed : 0);
                }}
                placeholder="English skills (0-10)"
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <FormInput
                type="checkbox"
                checked={form.hasSecondAccount}
                onChange={(valueOrEvent) =>
                  setField("hasSecondAccount", readCheckboxValue(valueOrEvent))
                }
              >
                I have a second account
              </FormInput>
              {form.hasSecondAccount ? (
                <FormInput
                  label="Second Account Name"
                  value={form.secondAccountName}
                  onChange={(valueOrEvent) =>
                    setField("secondAccountName", readInputValue(valueOrEvent))
                  }
                  placeholder="Second account name"
                  className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                />
              ) : null}
            </div>
          ) : null}

          {step === 3 ? (
            <div className="space-y-3">
              <FormTextarea
                label="CIT Journey"
                rows={5}
                value={form.citJourney}
                onChange={(valueOrEvent) => setField("citJourney", readInputValue(valueOrEvent))}
                placeholder="Your CIT journey (min 40 chars): when you started, preferred sides, and key milestones."
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <p className="text-xs text-white/60">{form.citJourney.length}/40 minimum chars</p>

              <FormTextarea
                label="Former Groups"
                rows={4}
                value={form.formerGroupsReason}
                onChange={(valueOrEvent) =>
                  setField("formerGroupsReason", readInputValue(valueOrEvent))
                }
                placeholder="Former groups and why you left or were removed (min 25 chars)."
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <p className="text-xs text-white/60">{form.formerGroupsReason.length}/25 minimum chars</p>

              <FormTextarea
                label="Why Join CODEBLACK?"
                rows={4}
                value={form.whyJoin}
                onChange={(valueOrEvent) => setField("whyJoin", readInputValue(valueOrEvent))}
                placeholder="Why do you want to join CODEBLACK and why should we accept you? (min 25 chars)."
                className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
              />
              <p className="text-xs text-white/60">{form.whyJoin.length}/25 minimum chars</p>
            </div>
          ) : null}

          {step === 4 ? (
            <div className="space-y-3">
              {[
                {
                  key: "punishlogImage",
                  label: "Punishlog Image",
                  validationLabel: "Punishlog image",
                },
                {
                  key: "statsImage",
                  label: "Stats Image",
                  validationLabel: "Stats image",
                },
                {
                  key: "historyImage",
                  label: "History Image",
                  validationLabel: "History image",
                },
              ].map((field) => {
                const value = form[field.key];
                const status = getImageValidationState(value, field.validationLabel);
                return (
                  <div key={field.key} className="space-y-1">
                    <FormInput
                      label={field.label}
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      onChange={(valueOrEvent) =>
                        setField(field.key, readFileValue(valueOrEvent))
                      }
                      className="w-full rounded-xl border border-white/15 bg-black/40 px-3 py-2 text-sm text-white"
                    />
                    <div
                      className={[
                        "flex items-center gap-2 text-xs",
                        status.isValid ? "text-emerald-100" : "text-rose-200",
                      ].join(" ")}
                    >
                      {status.isValid ? <CheckCircle2 size={13} /> : <CircleX size={13} />}
                      {status.isValid ? (
                        <>
                          <span className="truncate text-emerald-100">{status.fileName}</span>
                          <span className="text-emerald-200/85">({status.sizeLabel})</span>
                        </>
                      ) : (
                        <span>{status.message}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}

          {step === 5 ? (
            <div className="space-y-3">
              <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-white/80">
                <p className="whitespace-pre-line">{AGREEMENT_TEXT}</p>
              </div>
              <FormInput
                type="checkbox"
                checked={form.agreeTos}
                onChange={(valueOrEvent) =>
                  setField("agreeTos", readCheckboxValue(valueOrEvent))
                }
              >
                I agree to the platform ToS and review policy.
              </FormInput>
              <FormInput
                type="checkbox"
                checked={form.agreeLetter}
                onChange={(valueOrEvent) =>
                  setField("agreeLetter", readCheckboxValue(valueOrEvent))
                }
              >
                I confirm the agreement letter text above.
              </FormInput>
            </div>
          ) : null}

          <div className="flex flex-wrap justify-between gap-2">
            <Button
              variant="ghost"
              startContent={<ArrowLeft size={14} />}
              onPress={previousStep}
              isDisabled={step === 1}
            >
              Previous
            </Button>
            {step < 5 ? (
              <Button
                color="warning"
                endContent={<ArrowRight size={14} />}
                onPress={nextStep}
                isDisabled={!canMoveFromStep}
              >
                Next
              </Button>
            ) : (
              <Button
                color="success"
                onPress={handleSubmit}
                isPending={isSubmitting}
                isDisabled={!canMoveFromStep || isSubmitting}
              >
                {({ isPending }) => (
                  <>
                    {isPending ? <Spinner color="current" size="sm" /> : <CheckCircle2 size={14} />}
                    {isPending ? "Submitting..." : "Submit Application"}
                  </>
                )}
              </Button>
            )}
          </div>
        </Card.Content>
      </Card>

      {submitted ? (
        <Card className="border border-emerald-300/25 bg-emerald-300/10 shadow-2xl backdrop-blur-xl">
          <Card.Content className="space-y-2 px-6 py-5 text-emerald-100">
            <p className="font-semibold">Application Submitted</p>
            <p className="text-sm">
              Public ID: <code>{submitted.public_id}</code>
            </p>
            <p className="text-sm">Status: {submitted.status}</p>
          </Card.Content>
        </Card>
      ) : null}

      <Card className="border border-white/10 bg-black/40 p-4 backdrop-blur-xl">
        <div className="flex items-start gap-3 text-sm text-white/80">
          <ShieldAlert size={16} className="mt-0.5 text-amber-200" />
          <p>Application submission creates a dedicated voting context for authorized reviewers.</p>
        </div>
      </Card>
    </div>
  );
}
