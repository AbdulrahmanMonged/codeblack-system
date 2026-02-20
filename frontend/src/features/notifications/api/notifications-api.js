import { apiRequest } from "../../../core/api/http-client.js";

export async function listNotifications({
  unreadOnly = false,
  limit = 50,
  offset = 0,
} = {}) {
  const query = new URLSearchParams({
    unread_only: unreadOnly ? "true" : "false",
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/notifications?${query.toString()}`, { method: "GET" });
}

export async function getNotificationsUnreadCount() {
  return apiRequest("/notifications/unread-count", { method: "GET" });
}

export async function markNotificationRead(publicId) {
  return apiRequest(`/notifications/${publicId}/read`, { method: "POST" });
}

export async function markAllNotificationsRead() {
  return apiRequest("/notifications/read-all", { method: "POST" });
}

export async function deleteNotification(publicId) {
  return apiRequest(`/notifications/${publicId}`, { method: "DELETE" });
}

export async function deleteAllNotifications() {
  return apiRequest("/notifications", { method: "DELETE" });
}

export async function broadcastNotification(payload) {
  return apiRequest("/notifications/broadcast", {
    method: "POST",
    body: payload,
  });
}

export async function sendTargetedNotification(payload) {
  return apiRequest("/notifications/send-targeted", {
    method: "POST",
    body: payload,
  });
}
