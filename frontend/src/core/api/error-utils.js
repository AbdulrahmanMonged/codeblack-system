function safeJsonStringify(value) {
  try {
    return JSON.stringify(value);
  } catch {
    return "";
  }
}

function normalizeValidationErrors(items) {
  if (!Array.isArray(items)) {
    return "";
  }
  const messages = items
    .map((item) => {
      if (!item || typeof item !== "object") {
        return normalizeErrorText(item);
      }
      const path = Array.isArray(item.loc)
        ? item.loc
            .map((segment) => String(segment))
            .filter(Boolean)
            .join(".")
        : "";
      const message = typeof item.msg === "string" ? item.msg.trim() : normalizeErrorText(item.msg);
      if (!message) {
        return "";
      }
      return path ? `${path}: ${message}` : message;
    })
    .filter(Boolean);
  return messages.join("; ");
}

function normalizeErrorText(value) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string") {
    return value.trim();
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    const validationText = normalizeValidationErrors(value);
    if (validationText) {
      return validationText;
    }
    const joined = value.map((item) => normalizeErrorText(item)).filter(Boolean).join("; ");
    if (joined) {
      return joined;
    }
    return safeJsonStringify(value);
  }
  if (typeof value === "object") {
    const candidateFields = [
      value.message,
      value.error,
      value.error_description,
      value.detail,
      value.title,
      value.reason,
    ];
    for (const candidate of candidateFields) {
      const normalized = normalizeErrorText(candidate);
      if (normalized) {
        return normalized;
      }
    }

    const errorBag = value.errors;
    if (Array.isArray(errorBag)) {
      const fromArray = normalizeValidationErrors(errorBag);
      if (fromArray) {
        return fromArray;
      }
    } else if (errorBag && typeof errorBag === "object") {
      const fromErrorsObject = normalizeErrorText(Object.values(errorBag));
      if (fromErrorsObject) {
        return fromErrorsObject;
      }
    }

    return safeJsonStringify(value);
  }
  return String(value);
}

export function extractApiErrorMessage(error, fallback = "Request failed") {
  if (!error) {
    return fallback;
  }

  const fromMessage = normalizeErrorText(error?.message);
  if (fromMessage) {
    return fromMessage;
  }

  const fromDetails = normalizeErrorText(error?.details);
  if (fromDetails) {
    return fromDetails;
  }

  const fromError = normalizeErrorText(error?.error);
  if (fromError) {
    return fromError;
  }

  return normalizeErrorText(error) || fallback;
}

export function extractApiErrorCode(error) {
  return typeof error?.code === "string" ? error.code : "";
}
