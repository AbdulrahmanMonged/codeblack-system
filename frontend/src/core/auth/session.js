export function isAuthenticatedSession(status) {
  return status === "authenticated";
}

export function shouldHydrateSession(status) {
  return status === "unknown" || status === "hydrating";
}
