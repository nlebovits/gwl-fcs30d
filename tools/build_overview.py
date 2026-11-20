#!/usr/bin/env python3
"""Build the collection overview COG and the thumbnail for one year.

formats.md (Raster, Collection overviews): a collection of many rasters SHOULD
carry an overview COG, 8-bit RGB with optional alpha, in a web-map projection,
with the `visual` and `overview` roles, for at least the most recent period.

Each tile is read from the COG's own internal overview nearest the target
resolution, reprojected to EPSG:3857 with `mode` (the pixels are classes),
mosaicked, and coloured through the class table. Ocean (255) is alpha 0.

    uv run --with rasterio --with numpy --with pillow tools/build_overview.py \
        --staging ../gwl-fcs30d-data/staging --year 2022
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gwl import CLASSES, NODATA  # noqa: E402

os.environ.setdefault("GDAL_CACHEMAX", "256")  # per process; the default is 5% of RAM

HALF = 20037508.342789244  # Web Mercator half-extent, m
ZOOM = 7                   # 256 px tiles at z7: ~1.2 km/px at the equator
RES = 2 * HALF / (256 * 2**ZOOM)
MAX_LAT = 85.0511287798


def merc_y(lat: float) -> float:
    lat = max(min(lat, MAX_LAT), -MAX_LAT)
    return HALF / 180 * math.degrees(math.log(math.tan(math.radians(90 + lat) / 2)))


def warp_tile(path: str, grid: tuple) -> tuple[int, int, "np.ndarray"] | None:
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject

    x0, y_top = grid
    with rasterio.open(path) as probe:
        b, factors = probe.bounds, probe.overviews(1)
        src_res_m = probe.res[0] * 111_320
    # Pick the coarsest internal overview that is still finer than the target.
    level = max((i for i, f in enumerate(factors) if src_res_m * f <= RES), default=None)
    opts = {"OVERVIEW_LEVEL": level} if level is not None else {}
    col0 = max(0, math.floor((max(b.left, -180) * HALF / 180 - x0) / RES))
    col1 = math.ceil((min(b.right, 180) * HALF / 180 - x0) / RES)
    row0 = max(0, math.floor((y_top - merc_y(b.top)) / RES))
    row1 = math.ceil((y_top - merc_y(b.bottom)) / RES)
    if col1 <= col0 or row1 <= row0:
        return None
    out = np.full((row1 - row0, col1 - col0), NODATA, dtype="uint8")
    with rasterio.open(path, **opts) as src:
        reproject(
            rasterio.band(src, 1), out,
            dst_transform=from_origin(x0 + col0 * RES, y_top - row0 * RES, RES, RES),
            dst_crs="EPSG:3857", src_nodata=NODATA, dst_nodata=NODATA,
            resampling=Resampling.mode,
        )
    return row0, col0, out


def main() -> None:
    import numpy as np
    import rasterio
    import rasterio.shutil
    from PIL import Image
    from rasterio.transform import from_origin

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--staging", required=True, type=Path)
    ap.add_argument("--year", type=int, default=2022)
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()

    coll = a.staging / "gwl-fcs30d"
    tifs = sorted(str(p) for p in (coll / str(a.year)).glob("*/*/*.tif"))
    if not tifs:
        sys.exit(f"no COGs under {coll / str(a.year)}")
    tops, bottoms = [], []
    for p in tifs:
        with rasterio.open(p) as r:
            tops.append(r.bounds.top)
            bottoms.append(r.bounds.bottom)
    y_top, y_bot = merc_y(max(tops)), merc_y(min(bottoms))
    width, height = round(2 * HALF / RES), math.ceil((y_top - y_bot) / RES)
    mosaic = np.full((height, width), NODATA, dtype="uint8")
    with ProcessPoolExecutor(a.workers) as ex:
        for res in ex.map(warp_tile, tifs, [(-HALF, y_top)] * len(tifs)):
            if res is None:
                continue
            r0, c0, arr = res
            arr = arr[: height - r0, : width - c0]
            view = mosaic[r0:r0 + arr.shape[0], c0:c0 + arr.shape[1]]
            # Tiles overlap by about one pixel; never let a tile's ocean fill erase a neighbour.
            np.copyto(view, arr, where=arr != NODATA)
    print(f"{len(tifs)} tiles -> {width} x {height} px at {RES:.0f} m", flush=True)

    lut = np.zeros((256, 4), dtype="uint8")
    for v, c in CLASSES.items():
        lut[v] = (*c["rgb"], 0 if v == NODATA else 255)
    rgba = lut[mosaic]  # (h, w, 4)

    out = coll / f"overview-{a.year}.tif"
    tmp = f"/vsimem/overview-{a.year}.tif"
    profile = dict(driver="GTiff", width=width, height=height, count=4, dtype="uint8", crs="EPSG:3857",
                   transform=from_origin(-HALF, y_top, RES, RES), photometric="RGB", tiled=True,
                   blockxsize=512, blockysize=512)
    with rasterio.open(tmp, "w", **profile) as dst:
        dst.write(np.moveaxis(rgba, 2, 0))
        dst.colorinterp = [rasterio.enums.ColorInterp.red, rasterio.enums.ColorInterp.green,
                           rasterio.enums.ColorInterp.blue, rasterio.enums.ColorInterp.alpha]
    rasterio.shutil.copy(tmp, out, driver="COG", BLOCKSIZE=512, COMPRESS="ZSTD", LEVEL=9,
                         OVERVIEW_RESAMPLING="NEAREST", STATISTICS="YES", NUM_THREADS="ALL_CPUS")
    rasterio.shutil.delete(tmp)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")

    # Thumbnail: the overview's own colours over white, ~800 px on the long edge.
    scale = max(width, height) / 800
    small = mosaic[:: math.ceil(scale), :: math.ceil(scale)]
    rgb = lut[small][..., :3].copy()
    rgb[small == NODATA] = (255, 255, 255)
    # Small enough for git, and .png is outside upload_data.py's data allow-list.
    thumb = Path(__file__).resolve().parent.parent / "catalog" / "gwl-fcs30d" / "thumbnail.png"
    Image.fromarray(rgb).save(thumb, optimize=True)
    print(f"wrote {thumb} {small.shape[1]} x {small.shape[0]}")


if __name__ == "__main__":
    main()
