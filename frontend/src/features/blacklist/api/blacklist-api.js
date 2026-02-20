import { apiRequest } from "../../../core/api/http-client.js";

export async function checkBlacklistRemovalEligibility(accountName) {
  const query = new URLSearchParams({
    account_name: String(accountName || ""),
  });
  return apiRequest(`/blacklist/removal-requests/check?${query.toString()}`, {
    method: "GET",
  });
}

export async function submitBlacklistRemovalRequest(payload) {
  return apiRequest("/blacklist/removal-requests", {
    method: "POST",
    body: payload,
  });
}

export async function listBlacklistEntries({
  status,
  limit = 100,
  offset = 0,
} = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (status) {
    query.set("status", String(status));
  }
  return apiRequest(`/blacklist?${query.toString()}`, {
    method: "GET",
  });
}

export async function createBlacklistEntry(payload) {
  return apiRequest("/blacklist", {
    method: "POST",
    body: payload,
  });
}

export async function updateBlacklistEntry(entryId, payload) {
  return apiRequest(`/blacklist/${entryId}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function removeBlacklistEntry(entryId, payload) {
  return apiRequest(`/blacklist/${entryId}/remove`, {
    method: "POST",
    body: payload,
  });
}

export async function listBlacklistRemovalRequests({
  status,
  limit = 100,
  offset = 0,
} = {}) {
  const query = new URLSearchParams();
  if (status) {
    query.set("status", String(status));
  }
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  return apiRequest(`/blacklist/removal-requests?${query.toString()}`, {
    method: "GET",
  });
}

export async function getBlacklistRemovalRequestById(requestId) {
  return apiRequest(`/blacklist/removal-requests/${requestId}`, { method: "GET" });
}

export async function approveBlacklistRemovalRequest(requestId, payload) {
  return apiRequest(`/blacklist/removal-requests/${requestId}/approve`, {
    method: "POST",
    body: payload,
  });
}

export async function denyBlacklistRemovalRequest(requestId, payload) {
  return apiRequest(`/blacklist/removal-requests/${requestId}/deny`, {
    method: "POST",
    body: payload,
  });
}
