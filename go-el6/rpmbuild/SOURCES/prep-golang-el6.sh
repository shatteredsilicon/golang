#!/bin/bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
spec_file="$script_dir/../SPECS/golang.spec"

if [[ ! -f "$spec_file" ]]; then
  echo "error: spec file not found: $spec_file" >&2
  exit 1
fi

read_default_version() {
  local macro_name="$1"

  python3 - "$spec_file" "$macro_name" <<'PY'
import re
import sys

spec_file, macro_name = sys.argv[1:]
pattern = re.compile(r"^%\{!\?" + re.escape(macro_name) + r":\s*%global\s+" + re.escape(macro_name) + r"\s+([^}\s]+)\}")

with open(spec_file, encoding="utf-8") as spec:
    for line in spec:
        match = pattern.match(line.strip())
        if match:
            print(match.group(1))
            raise SystemExit(0)

raise SystemExit(1)
PY
}

GO_VERSION="${1:-${GO_VERSION:-$(read_default_version upstream_version)}}"
BOOTSTRAP_VERSION="${2:-${BOOTSTRAP_VERSION:-$(read_default_version bootstrap_version)}}"

python3 - "$GO_VERSION" <<'PY'
import re
import sys

version = sys.argv[1]
match = re.fullmatch(r"1\.(\d+)(?:\.(\d+))?", version)
if not match:
    raise SystemExit(f"error: unsupported Go version format: {version}")

minor = int(match.group(1))
if minor > 23:
    raise SystemExit(
        f"error: Go {version} is newer than the EL6 ceiling; use Go 1.23.x or older"
    )
PY

metadata_file="$(mktemp)"
trap 'rm -f "$metadata_file"' EXIT

wget \
  --quiet \
  --output-document="$metadata_file" \
  'https://go.dev/dl/?mode=json&include=all'

checksum_for() {
  local filename="$1"

  python3 - "$metadata_file" "$filename" <<'PY'
import json
import sys

metadata_file, filename = sys.argv[1:]

with open(metadata_file, encoding="utf-8") as stream:
    releases = json.load(stream)

for release in releases:
    for item in release.get("files", []):
        if item.get("filename") == filename:
            checksum = item.get("sha256", "")
            if not checksum:
                raise SystemExit(f"error: no SHA-256 found for {filename}")
            print(checksum)
            raise SystemExit(0)

raise SystemExit(f"error: {filename} not found in official Go download metadata")
PY
}

download_and_verify() {
  local filename="$1"
  local checksum
  local tmp_file="${filename}.tmp.$$"

  checksum="$(checksum_for "$filename")"

  rm -f "$tmp_file"
  wget \
    --tries=5 \
    --timeout=60 \
    --output-document="$tmp_file" \
    "https://go.dev/dl/${filename}"

  printf '%s  %s\n' "$checksum" "$tmp_file" | sha256sum -c -
  mv -f "$tmp_file" "$filename"
}

cd "$script_dir"

target_archive="go${GO_VERSION}.src.tar.gz"
bootstrap_archive="go${BOOTSTRAP_VERSION}.linux-amd64.tar.gz"

rm -f "$target_archive" "$bootstrap_archive"

download_and_verify "$target_archive"
download_and_verify "$bootstrap_archive"

printf 'Prepared EL6 Go sources:\n'
printf '  target:    %s\n' "$target_archive"
printf '  bootstrap: %s\n' "$bootstrap_archive"
