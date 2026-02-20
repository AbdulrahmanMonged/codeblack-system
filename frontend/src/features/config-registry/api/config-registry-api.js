import { apiRequest } from "../../../core/api/http-client.js";

export async function listConfigRegistry({
  includeSensitive = false,
} = {}) {
  const query = new URLSearchParams({
    include_sensitive: includeSensitive ? "true" : "false",
  });
  return apiRequest(`/config/registry?${query.toString()}`, { method: "GET" });
}

export async function previewConfigRegistryKey(key, payload) {
  return apiRequest(`/config/registry/${encodeURIComponent(String(key))}/preview`, {
    method: "POST",
    body: payload,
  });
}

export async function upsertConfigRegistryKey(key, payload) {
  return apiRequest(`/config/registry/${encodeURIComponent(String(key))}`, {
    method: "PUT",
    body: payload,
  });
}

export async function rollbackConfigRegistryKey(key, payload) {
  return apiRequest(`/config/registry/${encodeURIComponent(String(key))}/rollback`, {
    method: "POST",
    body: payload,
  });
}

export async function listConfigChanges({ limit = 100 } = {}) {
  return apiRequest(`/config/changes?limit=${encodeURIComponent(String(limit))}`, {
    method: "GET",
  });
}

export async function listConfigChangesAdvanced({
  limit = 100,
  includeSensitiveValues = false,
} = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    include_sensitive_values: includeSensitiveValues ? "true" : "false",
  });
  return apiRequest(`/config/changes?${query.toString()}`, { method: "GET" });
}

export async function approveConfigChange(changeId, payload) {
  return apiRequest(`/config/changes/${changeId}/approve`, {
    method: "POST",
    body: payload,
  });
}
