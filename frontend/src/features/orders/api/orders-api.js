import { apiRequest } from "../../../core/api/http-client.js";

export async function submitOrder(formData) {
  return apiRequest("/orders", {
    method: "POST",
    body: formData,
  });
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
