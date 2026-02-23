import { apiRequest } from "../../../core/api/http-client.js";

export async function listPlayers({ limit = 100, offset = 0 } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/playerbase?${query.toString()}`, { method: "GET" });
}

export async function createPlayer(payload) {
  return apiRequest("/playerbase", {
    method: "POST",
    body: payload,
  });
}

export async function getPlayer(playerId) {
  return apiRequest(`/playerbase/${playerId}`, { method: "GET" });
}

export async function listPunishments(playerId) {
  return apiRequest(`/playerbase/${playerId}/punishments`, { method: "GET" });
}

export async function createPunishment(playerId, payload) {
  return apiRequest(`/playerbase/${playerId}/punishments`, {
    method: "POST",
    body: payload,
  });
}

export async function updatePunishment(playerId, punishmentId, payload) {
  return apiRequest(`/playerbase/${playerId}/punishments/${punishmentId}`, {
    method: "PATCH",
    body: payload,
  });
}
