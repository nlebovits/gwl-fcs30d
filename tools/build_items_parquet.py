#!/usr/bin/env python3
"""Write the collection's STAC-GeoParquet item mirror, items.parquet.

formats.md (Raster, Item mirror): one row per item, registered as a
`collection-mirror` asset, spatially ordered, with per-row-group bbox
statistics. Built from the committed item JSON, so it always reproduces it.

Item hrefs are relative to each item's JSON file, which means nothing inside a
standalone Parquet file, so every relative href is resolved against the public
base URL. The values point at the same objects the item JSON does.

    uv run --with stac-geoparquet --with geoparquet-io tools/build_items_parquet.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish import load_config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COLLECTION = "gwl-fcs30d"


def main() -> None:
    import stac_geoparquet.arrow
    from geoparquet_io.api.table import Table

    cfg = load_config()
    base = cfg["public_base"].rstrip("/") + "/"
    cdir = ROOT / "catalog" / COLLECTION
    items = []
    for path in sorted(cdir.glob("*/*/*/*.json")):
        item = json.loads(path.read_text())
        if item.get("type") != "Feature":
            continue
        item_url = urljoin(base, str(path.relative_to(ROOT / "catalog")))
        for asset in item["assets"].values():
            asset["href"] = urljoin(item_url, asset["href"])
        for link in item["links"]:
            link["href"] = urljoin(item_url, link["href"])
        items.append(item)
    if not items:
        sys.exit(f"no items under {cdir}")
    table = stac_geoparquet.arrow.parse_stac_items_to_arrow(items).read_all()
    ordered = Table(table, geometry_column="geometry").sort_hilbert().to_arrow()
    ordered = ordered.replace_schema_metadata(table.schema.metadata)
    out = (ROOT / cfg["data_dir"]).resolve() / COLLECTION / "items.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    stac_geoparquet.arrow.to_parquet(ordered, out)
    print(f"wrote {out}: {len(items)} items, {out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
