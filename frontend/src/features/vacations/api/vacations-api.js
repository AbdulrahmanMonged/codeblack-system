import { apiRequest } from "../../../core/api/http-client.js";

export async function listVacations({
  status,
  playerId,
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
  if (playerId) {
    query.set("player_id", String(playerId));
  }
  return apiRequest(`/vacations?${query.toString()}`, { method: "GET" });
}

export async function createVacation(payload) {
  return apiRequest("/vacations", {
    method: "POST",
    body: payload,
  });
}

export async function getVacationPolicies() {
  return apiRequest("/vacations/policies", { method: "GET" });
}

export async function getVacationByPublicId(publicId) {
  return apiRequest(`/vacations/${publicId}`, { method: "GET" });
}

export async function approveVacation(publicId, payload) {
  return apiRequest(`/vacations/${publicId}/approve`, {
    method: "POST",
    body: payload,
  });
}

export async function denyVacation(publicId, payload) {
  return apiRequest(`/vacations/${publicId}/deny`, {
    method: "POST",
    body: payload,
  });
}

export async function cancelVacation(publicId) {
  return apiRequest(`/vacations/${publicId}/cancel`, {
    method: "POST",
  });
}

export async function markVacationReturned(publicId, payload) {
  return apiRequest(`/vacations/${publicId}/returned`, {
    method: "POST",
    body: payload,
  });
}
