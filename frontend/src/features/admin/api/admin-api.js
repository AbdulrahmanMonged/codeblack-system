import { apiRequest } from "../../../core/api/http-client.js";

function buildReviewQueueQuery({
  itemTypes,
  status,
  search,
  pendingOnly = true,
  limit = 50,
  offset = 0,
}) {
  const query = new URLSearchParams();
  if (Array.isArray(itemTypes)) {
    itemTypes
      .map((value) => String(value || "").trim())
      .filter(Boolean)
      .forEach((value) => query.append("item_type", value));
  }
  if (status) {
    query.set("status", String(status));
  }
  if (search) {
    query.set("search", String(search));
  }
  query.set("pending_only", pendingOnly ? "true" : "false");
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  return query.toString();
}

export async function getDashboardSummary() {
  return apiRequest("/admin/dashboard/summary", { method: "GET" });
}

export async function getReviewQueue(params = {}) {
  const queryString = buildReviewQueueQuery(params);
  return apiRequest(`/admin/review-queue?${queryString}`, { method: "GET" });
}

function buildAuditTimelineQuery({
  eventTypes,
  actorUserId,
  search,
  limit = 50,
  offset = 0,
}) {
  const query = new URLSearchParams();
  if (Array.isArray(eventTypes)) {
    eventTypes
      .map((value) => String(value || "").trim())
      .filter(Boolean)
      .forEach((value) => query.append("event_type", value));
  }
  if (actorUserId) {
    query.set("actor_user_id", String(actorUserId));
  }
  if (search) {
    query.set("search", String(search));
  }
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  return query.toString();
}

export async function getAuditTimeline(params = {}) {
  const queryString = buildAuditTimelineQuery(params);
  return apiRequest(`/admin/audit/timeline?${queryString}`, { method: "GET" });
}
