#!/usr/bin/env bash
# Convert each year as soon as its zip is complete and matches Zenodo's MD5,
# so conversion overlaps the download. A year with failed tiles is reported
# and skipped; rerun after fixing, and finished tiles are skipped.
# Run it inside a memory-capped unit (RUNBOOK.md).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
D="$REPO/../gwl-fcs30d-data"
cd "$D/raw"
declare -A SIZE
while read -r s k; do SIZE[$k]=$s; done < <(jq -r '.files[]|"\(.size) \(.key)"' "$REPO/docs/research/zenodo-10068479.json")
for y in $(seq 2000 2022); do
  z="GWL_FCS30_$y.zip"
  until [ "$(stat -c %s "$z" 2>/dev/null || echo 0)" = "${SIZE[$z]}" ]; do sleep 30; done
  grep " $z\$" MD5SUMS | md5sum -c --quiet - || { echo "md5 mismatch: $z" >&2; exit 1; }
  echo "== $y $(date -u +%FT%TZ)"
  (cd "$REPO" && uv run -q --with rasterio --with numpy python -I tools/convert.py \
     --raw "$D/raw" --out "$D/staging" --facts "$D/facts" --years "$y" --workers 16) \
     || echo "!! $y had failed tiles; rerun after fixing"
done
echo "all years converted $(date -u +%FT%TZ)"
