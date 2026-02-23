export function toArray(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (Array.isArray(value?.items)) {
    return value.items;
  }
  if (Array.isArray(value?.data)) {
    return value.data;
  }
  return [];
}
