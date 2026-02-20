export function formatBytes(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value <= 0) {
    return "0 B";
  }
  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  const amount = value / 1024 ** exponent;
  return `${amount.toFixed(exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

export function clampTextPreview(text, max = 120) {
  const value = String(text || "");
  if (value.length <= max) {
    return value;
  }
  return `${value.slice(0, max)}...`;
}
