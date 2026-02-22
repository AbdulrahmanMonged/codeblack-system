const CDN_BASE = String(import.meta.env.VITE_MEDIA_CDN_BASE_URL || "").trim().replace(
  /\/+$/,
  "",
);

export function resolveMediaUrl(path) {
  const normalizedPath = `/${String(path || "").replace(/^\/+/, "")}`;
  if (!CDN_BASE) {
    return normalizedPath;
  }
  return `${CDN_BASE}${normalizedPath}`;
}
