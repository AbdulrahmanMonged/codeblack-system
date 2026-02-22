const DEFAULT_SEARCH_KEYS = [
  "id",
  "public_id",
  "item_id",
  "item_type",
  "membership_id",
  "player_id",
  "player.id",
  "player.ingame_name",
  "player.account_name",
  "account_name",
  "ingame_name",
  "in_game_nickname",
  "alias",
  "identity",
  "username",
  "title",
  "name",
  "summary",
  "event_type",
  "category",
  "config_key",
  "command_type",
  "stream_id",
  "status",
  "reason",
  "remarks",
  "mta_serial",
  "serial",
  "forum_url",
];

function readPath(source, path) {
  const parts = String(path || "").split(".").filter(Boolean);
  let current = source;
  for (const part of parts) {
    if (!current || typeof current !== "object") {
      return undefined;
    }
    current = current[part];
  }
  return current;
}

function appendPrimitive(values, raw) {
  if (raw === null || raw === undefined) {
    return;
  }
  if (typeof raw === "string" || typeof raw === "number" || typeof raw === "boolean") {
    values.push(String(raw).toLowerCase());
  }
}

function collectSearchValues(record, preferredKeys = []) {
  const values = [];
  const dedupedKeys = [...new Set([...preferredKeys, ...DEFAULT_SEARCH_KEYS])];

  for (const key of dedupedKeys) {
    appendPrimitive(values, readPath(record, key));
  }

  if (!record || typeof record !== "object") {
    return values;
  }

  Object.values(record).forEach((value) => {
    appendPrimitive(values, value);
    if (value && typeof value === "object" && !Array.isArray(value)) {
      Object.values(value).forEach((nestedValue) => appendPrimitive(values, nestedValue));
    }
  });

  return values;
}

export function includesSearchQuery(record, query, preferredKeys = []) {
  const normalizedQuery = String(query || "").trim().toLowerCase();
  if (!normalizedQuery) {
    return true;
  }
  const values = collectSearchValues(record, preferredKeys);
  return values.some((value) => value.includes(normalizedQuery));
}
