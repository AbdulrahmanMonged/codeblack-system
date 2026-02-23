const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api/v1";

function parseBooleanEnv(value, fallback = false) {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  const normalized = String(value).trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(normalized)) {
    return false;
  }

  return fallback;
}

const rawAppEnv = import.meta.env.VITE_APP_ENV || import.meta.env.MODE || "development";

export const API_BASE_URL = rawApiBaseUrl.replace(/\/+$/, "");
export const APP_ENV = String(rawAppEnv).trim().toLowerCase() || "development";
export const IS_DEVELOPMENT_ENV =
  Boolean(import.meta.env.DEV) ||
  ["development", "dev", "local", "test"].includes(APP_ENV);
export const FRONTEND_DEV_UNLOCK_ALL =
  parseBooleanEnv(import.meta.env.VITE_DEV_UNLOCK_ALL, false) && IS_DEVELOPMENT_ENV;
