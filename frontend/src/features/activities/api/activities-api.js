import { apiRequest } from "../../../core/api/http-client.js";

export async function listActivities({
  status,
  activityType,
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
  if (activityType) {
    query.set("activity_type", String(activityType));
  }
  return apiRequest(`/activities?${query.toString()}`, { method: "GET" });
}

export async function createActivity(payload) {
  return apiRequest("/activities", {
    method: "POST",
    body: payload,
  });
}

export async function getActivityByPublicId(publicId) {
  return apiRequest(`/activities/${publicId}`, { method: "GET" });
}

export async function approveActivity(publicId, payload) {
  return apiRequest(`/activities/${publicId}/approve`, {
    method: "POST",
    body: payload,
  });
}

export async function rejectActivity(publicId, payload) {
  return apiRequest(`/activities/${publicId}/reject`, {
    method: "POST",
    body: payload,
  });
}

export async function publishActivity(publicId, payload) {
  return apiRequest(`/activities/${publicId}/publish`, {
    method: "POST",
    body: payload,
  });
}

export async function addActivityParticipant(publicId, payload) {
  return apiRequest(`/activities/${publicId}/participants`, {
    method: "POST",
    body: payload,
  });
}
