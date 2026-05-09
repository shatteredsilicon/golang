#!/bin/bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
spec_file="$script_dir/../SPECS/golang.spec"

if [[ ! -f "$spec_file" ]]; then
  echo "error: spec file not found: $spec_file" >&2
  exit 1
fi

GO_VERSION="${1:-${GO_VERSION:-$(awk '
  /^%global[[:space:]]+upstream_version[[:space:]]+/ { print $3; found=1; exit }
  /^Version:[[:space:]]+/ && !found { print $2; exit }
' "$spec_file")}}"

if [[ -z "${GO_VERSION}" ]]; then
  echo "error: GO_VERSION is empty; pass a tag or define upstream_version/Version in golang.spec" >&2
  exit 1
fi

cd "$script_dir"

rm -f *.tar.gz

wget https://go.dev/dl/go${GO_VERSION}.src.tar.gz
