#!/usr/bin/env python3
"""Convert the upstream GWL_FCS30D yearly zips into Portolan COGs.

Reads each tile out of its zip through GDAL's /vsizip/ into a temporary tiled
GTiff beside its output, and works block by block, so a worker's memory stays
small. For every tile it writes one COG and one facts file:

    <out>/gwl-fcs30d/<year>/<block>/<item>/<item>.tif
    <facts>/<item>.json      size, sha256 multihash, stats, class pixel counts

The COG keeps the upstream pixels and grid unchanged. It adds what the
Portolan raster rules require (formats.md, Raster): 512 px tiles, internal
overviews, embedded statistics, and the embedded colour table that a
classified raster renders from. Overviews use `mode`, because the pixels are
class codes. Each output is read back and compared with its source, pixel for
pixel, before it is accepted.

    uv run --with rasterio --with numpy tools/convert.py \
        --raw ../gwl-fcs30d-data/raw --out ../gwl-fcs30d-data/staging \
        --facts ../gwl-fcs30d-data/facts [--years 2000 2001] [--workers 32]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gwl import CLASSES, NODATA, block_of, item_id  # noqa: E402

# GDAL's block cache defaults to 5% of RAM per process (~6 GB here); cap it per worker.
os.environ.setdefault("GDAL_CACHEMAX", "256")

TILE_RE = re.compile(r"GWL_FCS30D_(\d{4})Maps_([EW]\d+[NS]\d+)\.tif$")

COG_OPTIONS = dict(
    driver="COG",
    BLOCKSIZE=512,
    COMPRESS="ZSTD",
    LEVEL=9,
    # Measured on two sample tiles: predictor 2 grows these class rasters.
    PREDICTOR="NO",
    OVERVIEW_RESAMPLING="MODE",
    STATISTICS="YES",
    NUM_THREADS="1",
)


def convert(zip_path: str, member: str, year: int, tile: str, out_root: str, facts_root: str) -> str:
    # Streams block by block: a worker never holds a whole tile (18554 x 18554 px)
    # in memory. Full-tile arrays at 48 workers took the host down twice.
    import numpy as np
    import rasterio
    import rasterio.shutil

    iid = item_id(tile, year)
    dest = Path(out_root) / "gwl-fcs30d" / str(year) / block_of(tile) / iid / f"{iid}.tif"
    facts = Path(facts_root) / f"{iid}.json"
    if facts.exists() and dest.exists() and json.loads(facts.read_text())["file:size"] == dest.stat().st_size:
        return f"skip {iid}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    staged = dest.with_suffix(".src.tif")
    tmp_out = dest.with_suffix(".tif.part")

    # 1. Copy out of the zip to a tiled GTiff on disk, then set nodata and the
    #    colour table in place so the COG driver carries both over.
    rasterio.shutil.copy(f"/vsizip/{zip_path}/{member}", staged, driver="GTiff", TILED="YES",
                         BLOCKXSIZE=512, BLOCKYSIZE=512, COMPRESS="ZSTD", ZSTD_LEVEL=1)
    with rasterio.open(staged, "r+") as s:
        assert s.count == 1 and s.dtypes[0] == "uint8", (iid, s.count, s.dtypes)
        s.nodata = NODATA
        s.write_colormap(1, {v: c["rgb"] + (0 if v == NODATA else 255,) for v, c in CLASSES.items()})
    rasterio.shutil.copy(staged, tmp_out, **COG_OPTIONS)

    # 2. Verify the COG against the source and count classes, one block at a time.
    counts = np.zeros(256, dtype=np.int64)
    with rasterio.open(staged) as s, rasterio.open(tmp_out) as out:
        assert out.colormap(1) and out.nodata == NODATA and out.overviews(1), iid
        for _, w in out.block_windows(1):
            a = s.read(1, window=w)
            if not np.array_equal(a, out.read(1, window=w)):
                tmp_out.unlink()
                raise RuntimeError(f"{iid}: COG pixels differ from source in {w}")
            counts += np.bincount(a.ravel(), minlength=256)
        tags, bounds, shape, transform, crs = out.tags(1), out.bounds, out.shape, out.transform, out.crs
    unexpected = {v for v in np.flatnonzero(counts).tolist() if v not in CLASSES}
    if unexpected:
        tmp_out.unlink()
        raise RuntimeError(f"{iid}: values outside the published code list: {unexpected}")
    staged.unlink()
    os.replace(tmp_out, dest)

    sha = hashlib.sha256()
    with dest.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            sha.update(chunk)
    facts.parent.mkdir(parents=True, exist_ok=True)
    facts.write_text(json.dumps({
        "item_id": iid, "year": year, "tile": tile, "member": member,
        "zip": Path(zip_path).name, "href": str(dest.relative_to(out_root)),
        "file:size": dest.stat().st_size, "file:checksum": "1220" + sha.hexdigest(),
        "bbox": [bounds.left, bounds.bottom, bounds.right, bounds.top],
        "shape": list(shape), "transform": list(transform)[:6], "epsg": crs.to_epsg(),
        "statistics": {k.removeprefix("STATISTICS_").lower(): float(v) for k, v in tags.items() if k.startswith("STATISTICS_")},
        "class_pixel_counts": {str(v): int(counts[v]) for v in CLASSES if counts[v]},
    }))
    return f"ok {iid}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--facts", required=True, type=Path)
    ap.add_argument("--years", nargs="*", type=int, default=list(range(2000, 2023)))
    ap.add_argument("--tiles", nargs="*", help="limit to these tile codes (smoke tests)")
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()

    jobs = []
    for year in a.years:
        zp = (a.raw / f"GWL_FCS30_{year}.zip").resolve()
        for member in zipfile.ZipFile(zp).namelist():
            m = TILE_RE.search(member)
            if m and (not a.tiles or m.group(2) in a.tiles):
                assert int(m.group(1)) == year, member
                jobs.append((str(zp), member, year, m.group(2), str(a.out.resolve()), str(a.facts.resolve())))
    print(f"{len(jobs)} tiles", flush=True)
    failed = 0
    with ProcessPoolExecutor(a.workers) as ex:
        futs = {ex.submit(convert, *j): j for j in jobs}
        for n, f in enumerate(as_completed(futs), 1):
            try:
                msg = f.result()
            except Exception as e:  # report every failure, keep going, fail at the end
                failed += 1
                msg = f"FAIL {futs[f][1]}: {e!r}"
            if n % 100 == 0 or not msg.startswith(("ok", "skip")):
                print(f"[{n}/{len(jobs)}] {msg}", flush=True)
    print(f"done: {len(jobs) - failed} ok, {failed} failed", flush=True)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
