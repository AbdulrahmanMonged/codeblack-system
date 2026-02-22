import { ToastProvider, toast as herouiToast } from "@heroui/react";

let defaultTimeoutMs = 3500;

function withDefaultTimeout(options) {
  const normalized = options ?? {};
  if (normalized.timeout != null) {
    return normalized;
  }

  return {
    ...normalized,
    timeout: defaultTimeoutMs,
  };
}

function baseToast(message, options) {
  return herouiToast(message, withDefaultTimeout(options));
}

baseToast.success = (message, options) => herouiToast.success(message, withDefaultTimeout(options));
baseToast.warning = (message, options) => herouiToast.warning(message, withDefaultTimeout(options));
baseToast.info = (message, options) => herouiToast.info(message, withDefaultTimeout(options));
baseToast.danger = (message, options) => herouiToast.danger(message, withDefaultTimeout(options));
baseToast.error = (message, options) => herouiToast.danger(message, withDefaultTimeout(options));
baseToast.promise = (...args) => herouiToast.promise(...args);
baseToast.close = (key) => herouiToast.close(key);
baseToast.clear = () => herouiToast.clear();
baseToast.dismiss = (key) => {
  if (key) {
    herouiToast.close(key);
    return;
  }

  herouiToast.clear();
};
baseToast.pauseAll = () => herouiToast.pauseAll();
baseToast.resumeAll = () => herouiToast.resumeAll();

export const toast = baseToast;

export function Toaster({
  position = "top-right",
  duration = 3500,
  maxVisibleToasts = 5,
}) {
  defaultTimeoutMs = duration;

  return <ToastProvider placement={position} maxVisibleToasts={maxVisibleToasts} />;
}
