import { apiRequest } from "../../../core/api/http-client.js";

export async function listRoleMatrix() {
  return apiRequest("/permissions/role-matrix", { method: "GET" });
}

export async function updateRoleMatrix(discordRoleId, payload) {
  return apiRequest(`/permissions/role-matrix/${discordRoleId}`, {
    method: "PUT",
    body: payload,
  });
}
