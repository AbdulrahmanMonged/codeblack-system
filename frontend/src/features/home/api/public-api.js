import { apiRequest } from "../../../core/api/http-client.js";

export async function listPublicPosts({ limit = 20, offset = 0 } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/public/posts?${query.toString()}`, { method: "GET" });
}



export async function getPublicPost(publicId) {
  return apiRequest(`/public/posts/${encodeURIComponent(String(publicId || "").trim())}`, {
    method: "GET",
  });
}

export async function getPublicMetrics() {
  return apiRequest("/public/metrics", { method: "GET" });
}

export async function listPublicRoster({ limit = 100, offset = 0 } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/public/roster?${query.toString()}`, { method: "GET" });
}
