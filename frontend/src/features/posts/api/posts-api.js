import { apiRequest } from "../../../core/api/http-client.js";

export async function listPosts({ publishedOnly = false, limit = 100, offset = 0 } = {}) {
  const query = new URLSearchParams({
    published_only: publishedOnly ? "true" : "false",
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/posts?${query.toString()}`, { method: "GET" });
}

export async function createPost(payload) {
  return apiRequest("/posts", {
    method: "POST",
    body: payload,
  });
}

export async function updatePost(publicId, payload) {
  return apiRequest(`/posts/${publicId}`, {
    method: "PATCH",
    body: payload,
  });
}

export async function publishPost(publicId, isPublished) {
  return apiRequest(`/posts/${publicId}/publish`, {
    method: "POST",
    body: { is_published: Boolean(isPublished) },
  });
}

export async function uploadPostMedia(file) {
  const body = new FormData();
  body.append("media_file", file);
  return apiRequest("/posts/media/upload", {
    method: "POST",
    body,
  });
}
