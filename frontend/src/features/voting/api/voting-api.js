import { apiRequest } from "../../../core/api/http-client.js";

export async function getVotingContext(contextType, contextId) {
  return apiRequest(`/voting/${contextType}/${contextId}`, { method: "GET" });
}

export async function castVote(contextType, contextId, payload) {
  return apiRequest(`/voting/${contextType}/${contextId}/vote`, {
    method: "POST",
    body: payload,
  });
}

export async function castApplicationVote(applicationId, payload) {
  return apiRequest(`/voting/application/${applicationId}/vote`, {
    method: "POST",
    body: payload,
  });
}

export async function listVotingVoters(contextType, contextId) {
  return apiRequest(`/voting/${contextType}/${contextId}/voters`, {
    method: "GET",
  });
}

export async function listApplicationVoters(applicationId) {
  return apiRequest(`/voting/application/${applicationId}/voters`, {
    method: "GET",
  });
}

export async function closeVoting(contextType, contextId, payload) {
  return apiRequest(`/voting/${contextType}/${contextId}/close`, {
    method: "POST",
    body: payload,
  });
}

export async function reopenVoting(contextType, contextId, payload) {
  return apiRequest(`/voting/${contextType}/${contextId}/reopen`, {
    method: "POST",
    body: payload,
  });
}

export async function resetVoting(contextType, contextId, payload) {
  return apiRequest(`/voting/${contextType}/${contextId}/reset`, {
    method: "POST",
    body: payload,
  });
}

export async function decideApplicationFromVoting(applicationId, payload) {
  return apiRequest(`/voting/application/${applicationId}/decision`, {
    method: "POST",
    body: payload,
  });
}
