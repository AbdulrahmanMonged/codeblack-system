import { apiRequest } from "../../../core/api/http-client.js";

export async function listConfigRegistry({
  includeSensitive = false,
  limit = 100,
  offset = 0,
} = {}) {
  const query = new URLSearchParams({
    include_sensitive: includeSensitive ? "true" : "false",
    limit: String(limit),
    offset: String(offset),
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

export async function listConfigChanges({ limit = 100, offset = 0 } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/config/changes?${query.toString()}`, {
    method: "GET",
  });
}

export async function listConfigChangesAdvanced({
  limit = 100,
  offset = 0,
  includeSensitiveValues = false,
} = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
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
