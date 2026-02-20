import { apiRequest } from "../../../core/api/http-client.js";

export async function checkApplicationEligibility(accountName) {
  const query = new URLSearchParams({ account_name: String(accountName || "") });
  return apiRequest(`/applications/eligibility?${query.toString()}`, { method: "GET" });
}

export async function submitApplication(formData) {
  return apiRequest("/applications", {
    method: "POST",
    body: formData,
  });
}

export async function listApplications({ status, limit = 100, offset = 0 } = {}) {
  const query = new URLSearchParams();
  if (status) {
    query.set("status", String(status));
  }
  query.set("limit", String(limit));
  query.set("offset", String(offset));
  return apiRequest(`/applications?${query.toString()}`, { method: "GET" });
}

export async function getApplicationByPublicId(publicId) {
  return apiRequest(`/applications/${publicId}`, { method: "GET" });
}

export async function decideApplication(publicId, payload) {
  return apiRequest(`/applications/${publicId}/decision`, {
    method: "POST",
    body: payload,
  });
}
