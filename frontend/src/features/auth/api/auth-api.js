import { apiRequest } from "../../../core/api/http-client.js";

export async function createDiscordLogin({ nextUrl = "/dashboard" } = {}) {
  const query = new URLSearchParams();
  if (nextUrl) {
    query.set("next_url", nextUrl);
  }
  const suffix = query.toString() ? `?${query.toString()}` : "";
  return apiRequest(`/auth/discord/login${suffix}`, { method: "GET" });
}

export async function exchangeDiscordCallback({ code, state }) {
  const query = new URLSearchParams({
    code: String(code),
    state: String(state),
  });
  return apiRequest(`/auth/discord/callback?${query.toString()}`, { method: "GET" });
}

export async function logoutSession() {
  return apiRequest("/auth/logout", { method: "POST" });
}
