import { apiRequest } from "../../../core/api/http-client.js";

export async function getBotChannels() {
  return apiRequest("/bot/channels", { method: "GET" });
}

export async function updateBotChannels(payload) {
  return apiRequest("/bot/channels", {
    method: "PUT",
    body: payload,
  });
}

export async function getBotFeatures() {
  return apiRequest("/bot/features", { method: "GET" });
}

export async function updateBotFeatures(payload) {
  return apiRequest("/bot/features", {
    method: "PUT",
    body: payload,
  });
}

export async function triggerBotForumSync() {
  return apiRequest("/bot/triggers/forum-sync", {
    method: "POST",
  });
}

export async function triggerBotCopScoresRefresh() {
  return apiRequest("/bot/triggers/cop-scores-refresh", {
    method: "POST",
  });
}

export async function listBotDeadLetters({ limit = 100, offset = 0 } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/bot/dead-letter?${query.toString()}`, {
    method: "GET",
  });
}

export async function replayBotDeadLetter(deadLetterId) {
  return apiRequest(`/bot/dead-letter/${deadLetterId}/replay`, {
    method: "POST",
  });
}
