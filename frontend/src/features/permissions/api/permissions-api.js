import { apiRequest } from "../../../core/api/http-client.js";

export async function listRoleMatrix({ limit = 100, offset = 0 } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiRequest(`/permissions/role-matrix?${query.toString()}`, { method: "GET" });
}

export async function updateRoleMatrix(discordRoleId, payload) {
  const roleId = encodeURIComponent(String(discordRoleId));
  return apiRequest(`/permissions/role-matrix/${roleId}`, {
    method: "PUT",
    body: payload,
  });
}
