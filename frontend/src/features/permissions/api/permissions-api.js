import { apiRequest } from "../../../core/api/http-client.js";

export async function listPermissionCatalog() {
  return apiRequest("/permissions/catalog", { method: "GET" });
}

export async function listRoleMatrix({ limit = 100, offset = 0, syncRoles = false } = {}) {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  if (syncRoles) {
    query.set("sync", "true");
  }
  return apiRequest(`/permissions/role-matrix?${query.toString()}`, { method: "GET" });
}

export async function updateRoleMatrix(discordRoleId, payload) {
  const roleId = encodeURIComponent(String(discordRoleId));
  return apiRequest(`/permissions/role-matrix/${roleId}`, {
    method: "PUT",
    body: payload,
  });
}
