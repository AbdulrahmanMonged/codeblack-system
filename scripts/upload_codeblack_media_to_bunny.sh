#!/usr/bin/env bash
set -euo pipefail

DRY_RUN=0
SOURCE_DIR="codeblack-media"
ENV_FILE=".env"
KEY_PREFIX=""
MANIFEST_FILE="codeblack-media/cdn-manifest.tsv"

usage() {
  cat <<'USAGE'
Usage: scripts/upload_codeblack_media_to_bunny.sh [options]

Options:
  --dry-run                 Print what would be uploaded without sending requests.
  --source <dir>            Source media directory (default: codeblack-media).
  --env-file <file>         Env file to read Bunny config from (default: .env).
  --prefix <path>           Optional key prefix inside Bunny zone.
  --manifest <file>         Output manifest path (default: codeblack-media/cdn-manifest.tsv).
  -h, --help                Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --source)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --prefix)
      KEY_PREFIX="$2"
      shift 2
      ;;
    --manifest)
      MANIFEST_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_cmd curl
require_cmd find
require_cmd sort

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "Source directory not found: $SOURCE_DIR" >&2
  exit 1
fi

read_env_value() {
  local key="$1"
  local file="$2"
  if [[ ! -f "$file" ]]; then
    echo ""
    return
  fi
  local line
  line="$(grep -m1 -E "^${key}=" "$file" || true)"
  if [[ -z "$line" ]]; then
    echo ""
    return
  fi
  line="${line#*=}"
  line="${line%$'\r'}"
  echo "$line"
}

normalize_base_url() {
  local raw="${1:-}"
  raw="${raw%/}"
  if [[ -z "$raw" ]]; then
    echo ""
    return
  fi
  if [[ "$raw" != http://* && "$raw" != https://* ]]; then
    raw="https://${raw#/}"
  fi
  echo "${raw%/}"
}

infer_content_type_from_extension() {
  local lower_path="${1,,}"
  case "$lower_path" in
    *.png) echo "image/png" ;;
    *.jpg|*.jpeg) echo "image/jpeg" ;;
    *.gif) echo "image/gif" ;;
    *.webp) echo "image/webp" ;;
    *.svg) echo "image/svg+xml" ;;
    *.avif) echo "image/avif" ;;
    *.mp4) echo "video/mp4" ;;
    *.webm) echo "video/webm" ;;
    *.mov) echo "video/quicktime" ;;
    *.mp3) echo "audio/mpeg" ;;
    *.wav) echo "audio/wav" ;;
    *.ogg) echo "audio/ogg" ;;
    *.flac) echo "audio/flac" ;;
    *.woff) echo "font/woff" ;;
    *.woff2) echo "font/woff2" ;;
    *.ttf) echo "font/ttf" ;;
    *.otf) echo "font/otf" ;;
    *) echo "application/octet-stream" ;;
  esac
}

is_media_content_type() {
  case "$1" in
    image/*|video/*|audio/*|font/*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_media_extension() {
  local lower_path="${1,,}"
  case "$lower_path" in
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.svg|*.avif|*.mp4|*.webm|*.mov|*.mp3|*.wav|*.ogg|*.flac|*.woff|*.woff2|*.ttf|*.otf)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

BUNNY_ENDPOINT="${BUNNY_STORAGE_ENDPOINT:-}"
BUNNY_ZONE="${BUNNY_STORAGE_ZONE:-}"
BUNNY_ACCESS_KEY="${BUNNY_STORAGE_ACCESS_KEY:-}"
BUNNY_PUBLIC_BASE="${BUNNY_STORAGE_PUBLIC_BASE_URL:-}"

if [[ -z "$BUNNY_ENDPOINT" ]]; then
  BUNNY_ENDPOINT="$(read_env_value "BUNNY_STORAGE_ENDPOINT" "$ENV_FILE")"
fi
if [[ -z "$BUNNY_ZONE" ]]; then
  BUNNY_ZONE="$(read_env_value "BUNNY_STORAGE_ZONE" "$ENV_FILE")"
fi
if [[ -z "$BUNNY_ACCESS_KEY" ]]; then
  BUNNY_ACCESS_KEY="$(read_env_value "BUNNY_STORAGE_ACCESS_KEY" "$ENV_FILE")"
fi
if [[ -z "$BUNNY_PUBLIC_BASE" ]]; then
  BUNNY_PUBLIC_BASE="$(read_env_value "BUNNY_STORAGE_PUBLIC_BASE_URL" "$ENV_FILE")"
fi

BUNNY_ENDPOINT="$(normalize_base_url "$BUNNY_ENDPOINT")"
BUNNY_PUBLIC_BASE="$(normalize_base_url "$BUNNY_PUBLIC_BASE")"

if [[ -z "$BUNNY_ENDPOINT" || -z "$BUNNY_ZONE" || -z "$BUNNY_ACCESS_KEY" ]]; then
  echo "Missing Bunny config. Required: BUNNY_STORAGE_ENDPOINT, BUNNY_STORAGE_ZONE, BUNNY_STORAGE_ACCESS_KEY" >&2
  exit 1
fi

if [[ "$BUNNY_ZONE" == *.* ]]; then
  echo "Warning: BUNNY_STORAGE_ZONE looks like a hostname ($BUNNY_ZONE). It should usually be a storage zone name." >&2
fi

KEY_PREFIX="${KEY_PREFIX#/}"
KEY_PREFIX="${KEY_PREFIX%/}"
if [[ -n "$KEY_PREFIX" ]]; then
  KEY_PREFIX="${KEY_PREFIX}/"
fi

manifest_abs="$MANIFEST_FILE"
if [[ "$manifest_abs" != /* ]]; then
  manifest_abs="${REPO_ROOT}/${manifest_abs}"
fi
source_abs="$SOURCE_DIR"
if [[ "$source_abs" != /* ]]; then
  source_abs="${REPO_ROOT}/${source_abs}"
fi
manifest_rel_skip=""
if [[ "$manifest_abs" == "$source_abs/"* ]]; then
  manifest_rel_skip="${manifest_abs#${source_abs}/}"
fi

mapfile -d '' FILES < <(find "$SOURCE_DIR" -type f -print0 | sort -z)
if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No files found under $SOURCE_DIR"
  exit 0
fi

mkdir -p "$(dirname "$MANIFEST_FILE")"
: > "$MANIFEST_FILE"

uploaded=0
failed=0
skipped=0

for file_path in "${FILES[@]}"; do
  rel_path="${file_path#${SOURCE_DIR}/}"

  if [[ -n "$manifest_rel_skip" && "$rel_path" == "$manifest_rel_skip" ]]; then
    printf 'SKIP     %-45s -> generated manifest\n' "$rel_path"
    skipped=$((skipped + 1))
    continue
  fi

  case "${rel_path##*/}" in
    cdn-manifest.tsv)
      printf 'SKIP     %-45s -> manifest artifact\n' "$rel_path"
      skipped=$((skipped + 1))
      continue
      ;;
  esac

  content_type=""
  if command -v file >/dev/null 2>&1; then
    content_type="$(file --brief --mime-type "$file_path" 2>/dev/null || true)"
  fi
  if [[ -z "$content_type" ]]; then
    content_type="$(infer_content_type_from_extension "$rel_path")"
  fi

  if ! is_media_content_type "$content_type" && ! is_media_extension "$rel_path"; then
    printf 'SKIP     %-45s -> non-media file (%s)\n' "$rel_path" "$content_type"
    skipped=$((skipped + 1))
    continue
  fi

  key="${KEY_PREFIX}${rel_path}"
  upload_url="${BUNNY_ENDPOINT}/${BUNNY_ZONE}/${key}"

  if [[ -n "$BUNNY_PUBLIC_BASE" ]]; then
    public_url="${BUNNY_PUBLIC_BASE}/${key}"
  else
    public_url="$upload_url"
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'DRY RUN  %-45s -> %s\n' "$rel_path" "$public_url"
    printf '%s\t%s\n' "$rel_path" "$public_url" >> "$MANIFEST_FILE"
    uploaded=$((uploaded + 1))
    continue
  fi

  http_code="$(curl -sS -o /dev/null -w '%{http_code}' \
    -X PUT \
    -H "AccessKey: ${BUNNY_ACCESS_KEY}" \
    -H "Content-Type: ${content_type}" \
    --data-binary "@${file_path}" \
    "$upload_url")"

  if [[ "$http_code" =~ ^2 ]]; then
    printf 'UPLOADED %-45s -> %s\n' "$rel_path" "$public_url"
    printf '%s\t%s\n' "$rel_path" "$public_url" >> "$MANIFEST_FILE"
    uploaded=$((uploaded + 1))
  else
    printf 'FAILED   %-45s -> status %s\n' "$rel_path" "$http_code" >&2
    failed=$((failed + 1))
  fi
done

echo "Upload summary: uploaded=${uploaded}, failed=${failed}, skipped=${skipped}, manifest=${MANIFEST_FILE}"

if [[ "$failed" -gt 0 ]]; then
  exit 1
fi
