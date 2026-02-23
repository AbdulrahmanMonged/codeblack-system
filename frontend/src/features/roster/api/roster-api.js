import { apiRequest } from "../../../core/api/http-client.js";

export async function listRoster({ limit = 100, offset = 0 } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/roster?${query.toString()}`, { method: "GET" });
}

export async function createRosterMembership(payload) {
  return apiRequest("/roster", {
    method: "POST",
    body: payload,
  });
}

export async function updateRosterMembership(membershipId, payload) {
  return apiRequest(`/roster/${membershipId}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function listRanks() {
  return apiRequest("/roster/ranks", { method: "GET" });
}

export async function createRank(payload) {
  return apiRequest("/roster/ranks", {
    method: "POST",
    body: payload,
  });
}
