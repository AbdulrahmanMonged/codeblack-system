import { apiRequest } from "../../../core/api/http-client.js";

export async function submitOrder(formData) {
  return apiRequest("/orders", {
    method: "POST",
    body: formData,
  });
}

export async function listMyOrders({ status = null, limit = 20, offset = 0 } = {}) {
  const query = new URLSearchParams();
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  if (status) {
    query.set("status", String(status));
  }
  return apiRequest(`/orders/mine?${query.toString()}`, { method: "GET" });
}

export async function getAccountLinkByUserId(userId) {
  return apiRequest(`/users/${userId}/account-link`, { method: "GET" });
}

export async function getOrderByPublicId(publicId) {
  return apiRequest(`/orders/${publicId}`, { method: "GET" });
}

export async function decideOrder(publicId, payload) {
  return apiRequest(`/orders/${publicId}/decision`, {
    method: "POST",
    body: payload,
  });
}
