import { apiRequest } from "../../../core/api/http-client.js";

export async function createVerificationRequest(payload) {
  return apiRequest("/verification-requests", {
    method: "POST",
    body: payload,
  });
}

export async function getMyVerificationRequest() {
  return apiRequest("/verification-requests/me", {
    method: "GET",
  });
}

export async function listVerificationRequests({
  status,
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
  return apiRequest(`/verification-requests?${query.toString()}`, {
    method: "GET",
  });
}

export async function getVerificationRequestByPublicId(publicId) {
  return apiRequest(`/verification-requests/${publicId}`, {
    method: "GET",
  });
}

export async function approveVerificationRequest(publicId, payload) {
  return apiRequest(`/verification-requests/${publicId}/approve`, {
    method: "POST",
    body: payload,
  });
}

export async function denyVerificationRequest(publicId, payload) {
  return apiRequest(`/verification-requests/${publicId}/deny`, {
    method: "POST",
    body: payload,
  });
}
