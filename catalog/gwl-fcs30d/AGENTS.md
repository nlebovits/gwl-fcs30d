# AGENTS.md — GWL_FCS30D annual wetland maps

[Open in data browser](https://browser.portolan-sdi.org/#/external/data.source.coop/portolan-mirrors/gwl-fcs30d/gwl-fcs30d/collection.json) · [Source repository](https://github.com/nlebovits/gwl-fcs30d) · [Report a problem](https://github.com/nlebovits/gwl-fcs30d/issues) · [Hosting repository](https://source.coop/portolan-mirrors/gwl-fcs30d)

Every claim here is quoted from a source or measured from the data. The
[README](README.md) gives the sources.

## What the data is

- One item per 5° tile per year, 2000 to 2022. Item id `<tile>_<year>`, for
  example `E100N25_2022`. The tile code names the upper-left corner.
- Each item has one asset, `data`: a single-band uint8 COG in EPSG:4326.
- Pixel values are class codes:

| Code | Class |
|---|---|
| 0 | Non-wetland (a class, not missing data) |
| 180 | Permanent water |
| 181 | Swamp |
| 182 | Marsh |
| 183 | Flooded flat |
| 184 | Saline |
| 185 | Mangrove forest |
| 186 | Salt marsh |
| 187 | Tidal flat |
| 188 | Undocumented. In the files, absent from the producers' code list |
| 255 | Ocean, outside the mapped area. The declared nodata |

The same list, with definitions, is `item_assets.data["classification:classes"]`
in `collection.json`.

## Find tiles: query `items.parquet`, do not walk the tree

The tree has more than 22,000 item files. `items.parquet` has the same items,
one row each. Hrefs in it are absolute.

```sql
INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs;
-- 2022 tiles that intersect the Sundarbans
SELECT id, assets.data.href
FROM read_parquet('https://data.source.coop/portolan-mirrors/gwl-fcs30d/gwl-fcs30d/items.parquet')
WHERE start_datetime = TIMESTAMPTZ '2022-01-01 00:00:00+00'
  AND bbox.xmin < 89.9 AND bbox.xmax > 88.8 AND bbox.ymin < 22.4 AND bbox.ymax > 21.5;
```

```sql
-- One tile through time: 23 rows, one per year
SELECT year(start_datetime) AS year, assets.data.href
FROM read_parquet('https://data.source.coop/portolan-mirrors/gwl-fcs30d/gwl-fcs30d/items.parquet')
WHERE id LIKE 'E85N25\_%' ESCAPE '\'
ORDER BY year;
```

## Read pixels

Read a window over HTTP range requests. Weight each pixel by its area, because
the grid is in degrees.

```python
import numpy as np, rasterio
from rasterio.windows import from_bounds

href = "https://data.source.coop/portolan-mirrors/gwl-fcs30d/gwl-fcs30d/2022/E80-E100_N10-N30/E85N25_2022/E85N25_2022.tif"
west, south, east, north = 88.8, 21.5, 89.9, 22.4  # inside one tile

with rasterio.open(href) as src:
    win = from_bounds(west, south, east, north, src.transform)
    a = src.read(1, window=win)
    t = src.window_transform(win)
lat = t.f + (np.arange(a.shape[0]) + 0.5) * t.e  # pixel-centre latitudes
m = 111_320 * abs(t.a)                           # pixel size in m at the equator
area_km2 = (m * m * np.cos(np.radians(lat)))[:, None] / 1e6 * np.ones(a.shape[1])
for code in (180, 181, 182, 183, 184, 185, 186, 187):
    print(code, round(float(area_km2[a == code].sum()), 1), "km2")
```

The same COG opens in GDAL as `/vsicurl/<href>`.

## Quirks that produce silently wrong answers

- **`datetime` is null.** Each item covers a calendar year through
  `start_datetime` and `end_datetime`. Filter on `start_datetime`.
- **188 is undocumented.** It occurs in tiles `E55N65` (every year, about
  107,000 px a year), `E55S20` (every year, a few pixels) and `W55N75` (2011,
  2 px). Its meaning is unknown. Exclude it from per-class results or
  report it separately; do not fold it into a neighbouring class.
- **0 is not nodata.** Only 255 is. Treating 0 as nodata removes all
  non-wetland land from a share-of-land calculation.
- **Adjacent tiles overlap by about 0.75 px, and their grids are offset.** Each
  tile is 18,554 px of 0.000269494585235856°, which is 5.0002°. Pixels near a
  tile edge appear in two tiles. A sum over several tiles counts them twice
  unless you clip each tile to its nominal 5° cell first.
- **Pixel area depends on latitude.** About 30 m × 30 m × cos(latitude). A
  count of pixels is not an area.
- **Overviews use `mode`.** A zoomed-out read returns the most common class in
  each block, which hides small wetlands. Compute areas at full resolution.
- **The band statistics count 0.** `mean` and `stddev` in the COG header are
  over class codes and mean nothing as numbers. They exist for renderers.
- **`overview-2022.tif` is a picture.** RGBA in EPSG:3857 at about 1.2 km. It
  has no class codes.
