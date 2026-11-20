#!/usr/bin/env bash
# Download every file in Zenodo record 10068479 into ../gwl-fcs30d-data/raw,
# verify each against Zenodo's MD5, and record sha256 multihashes for the
# `source` assets. Resumable: rerun after an interruption.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RAW="$REPO/../gwl-fcs30d-data/raw"
mkdir -p "$RAW" && cd "$RAW"
jq -r '.files[] | "\(.checksum|sub("md5:";""))  \(.key)"' "$REPO/docs/research/zenodo-10068479.json" > MD5SUMS
cut -c35- MD5SUMS | xargs -P 4 -I{} curl -sSfL --retry 10 --retry-all-errors -C - -o {} "https://zenodo.org/records/10068479/files/{}"
md5sum -c MD5SUMS
for f in $(cut -c35- MD5SUMS); do printf '%s\t1220%s\n' "$f" "$(sha256sum "$f" | cut -c1-64)"; done \
  | python3 -c 'import sys,json; print(json.dumps(dict(l.rstrip("\n").split("\t") for l in sys.stdin), indent=2))' \
  > "$REPO/docs/research/zenodo-10068479-sha256.json"
