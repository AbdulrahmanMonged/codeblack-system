import { API_BASE_URL } from "../config/env.js";

class ApiHttpError extends Error {
  constructor({ status, code, message, details }) {
    super(normalizeErrorText(message) || "Request failed");
    this.name = "ApiHttpError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

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

function normalizePath(path) {
  if (!path) {
    return API_BASE_URL;
  }

  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

function isMutationMethod(method) {
  const normalized = String(method || "GET").toUpperCase();
  return normalized !== "GET" && normalized !== "HEAD" && normalized !== "OPTIONS";
}

function getCsrfTokenFromMeta() {
  if (typeof document === "undefined") {
    return "";
  }
  const tag = document.querySelector('meta[name="csrf-token"]');
  return tag?.getAttribute("content") || "";
}

async function readBody(response) {
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

function looksLikeHtmlPayload(payload) {
  if (typeof payload !== "string") {
    return false;
  }
  const trimmed = payload.trim().toLowerCase();
  return trimmed.startsWith("<!doctype html") || trimmed.startsWith("<html");
}

export async function apiRequest(path, init = {}) {
  const { body, headers: providedHeaders, ...restInit } = init;
  const headers = new Headers(providedHeaders || {});
  const method = String(restInit.method || "GET").toUpperCase();
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;

  let resolvedBody = body;
  if (body !== undefined && body !== null && !isFormData && typeof body !== "string") {
    resolvedBody = JSON.stringify(body);
  }

  if (!isFormData && resolvedBody !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json, text/plain;q=0.9, */*;q=0.8");
  }
  if (isMutationMethod(method) && !headers.has("X-CSRF-Token")) {
    const csrfToken = getCsrfTokenFromMeta();
    if (csrfToken) {
      headers.set("X-CSRF-Token", csrfToken);
    }
  }

  const response = await fetch(normalizePath(path), {
    ...restInit,
    method,
    credentials: "include",
    headers,
    body: resolvedBody,
  });

  const payload = await readBody(response);
  if (response.ok) {
    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    if (response.status !== 204 && !isJson && looksLikeHtmlPayload(payload)) {
      throw new ApiHttpError({
        status: 502,
        code: "INVALID_API_RESPONSE",
        message:
          "Received HTML instead of JSON from API. Backend might be unavailable or API base URL is misconfigured.",
        details: {
          path: normalizePath(path),
          content_type: contentType,
        },
      });
    }
    return payload;
  }

  const errorMessage = normalizeErrorText(payload) || `Request failed with status ${response.status}`;

  throw new ApiHttpError({
    status: response.status,
    code: typeof payload === "object" && payload !== null ? payload.error_code : undefined,
    message: errorMessage,
    details: payload,
  });
}

export async function apiFetcher(resource) {
  if (Array.isArray(resource)) {
    const [path, init] = resource;
    return apiRequest(path, init ?? {});
  }
  return apiRequest(resource, { method: "GET" });
}

export { ApiHttpError };
