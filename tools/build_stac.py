#!/usr/bin/env python3
"""Generate the STAC tree under catalog/ from the conversion facts.

    python3 tools/build_stac.py --facts ../gwl-fcs30d-data/facts

Layout (core.md, Raster Collections and Nested Catalogs):

    catalog.json                                  root
    gwl-fcs30d/collection.json                    one collection, all years
    gwl-fcs30d/<year>/catalog.json                23 year catalogs
    gwl-fcs30d/<year>/<block>/catalog.json        20 deg blocks, <= 16 tiles each
    gwl-fcs30d/<year>/<block>/<item>/<item>.json  one item per tile-year scene

Each tile-year is a scene, so each is an item with an item-level COG
(PORTO-CORE-071). Year and block catalogs keep every catalog and the
collection under twenty ungrouped children (PORTO-CORE-078).

Hand-written files are left alone: catalog/README.md, catalog/AGENTS.md, and
the collection's README.md and AGENTS.md. The generator writes everything
else, and a second run with the same facts changes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gwl import (  # noqa: E402
    CLASSES, DATASET_CITATION, MIRRORED, NODATA, PAPER_CITATION, PAPER_DOI, YEARS,
    ZENODO_DOI, ZENODO_RECORD, block_bounds, block_title,
)
from publish import load_config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "catalog"
COLLECTION = "gwl-fcs30d"
ZENODO = json.loads((ROOT / "docs/research/zenodo-10068479.json").read_text())
_SHA = ROOT / "docs/research/zenodo-10068479-sha256.json"
SOURCE_SHA256: dict[str, str] = json.loads(_SHA.read_text()) if _SHA.exists() else {}

PORTOLAN = "https://schemas.portolan-sdi.org/portolan/v0.3.0/schema.json"
EXT = {
    "classification": "https://stac-extensions.github.io/classification/v2.0.0/schema.json",
    "projection": "https://stac-extensions.github.io/projection/v2.0.0/schema.json",
    "file": "https://stac-extensions.github.io/file/v2.1.0/schema.json",
    "scientific": "https://stac-extensions.github.io/scientific/v1.0.0/schema.json",
}
COG = "image/tiff; application=geotiff; profile=cloud-optimized"
JSON, GEOJSON, MD, HTML = "application/json", "application/geo+json", "text/markdown", "text/html"


def classes() -> list[dict]:
    out = []
    for value, c in CLASSES.items():
        cls = {"value": value, "name": c["name"], "title": c["title"], "description": c["description"]}
        if value == NODATA:
            cls["nodata"] = True
        else:
            cls["color_hint"] = "".join(f"{x:02X}" for x in c["rgb"])
        out.append(cls)
    return out


def clamp_bbox(b: list[float]) -> list[float]:
    # The producer's tiles are 18554 px of 1/3710.7 deg, a hair over 5 deg, so
    # edge tiles overrun +-180 / +-90 by ~0.0002 deg. bbox must stay in range.
    w, s, e, n = b
    return [max(w, -180.0), max(s, -90.0), min(e, 180.0), min(n, 90.0)]


def polygon(b: list[float]) -> dict:
    w, s, e, n = b
    return {"type": "Polygon", "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]}


def union(boxes) -> list[float]:
    boxes = list(boxes)
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def year_interval(year: int) -> tuple[str, str]:
    return f"{year}-01-01T00:00:00Z", f"{year}-12-31T23:59:59Z"


class Nav:
    """The four navigation links every catalog and collection carries
    (portolan-bootstrap reference/catalog-navigation.md)."""

    def __init__(self, cfg: dict[str, str]):
        self.base = cfg["public_base"].rstrip("/")
        self.repo = cfg["repository"].rstrip("/")
        self.hosting = cfg["hosting_page"].rstrip("/")
        self.browser = cfg["browser_route"].rstrip("/")

    def browser_url(self, rel_json: str) -> str:
        return f"{self.browser}/{self.base.removeprefix('https://')}/{rel_json}"

    def links(self, rel_json: str) -> list[dict]:
        return [
            {"rel": "alternate", "href": self.browser_url(rel_json), "type": HTML, "title": "Open in the Portolan data browser"},
            {"rel": "vcs", "href": self.repo, "type": HTML, "title": "Source repository"},
            {"rel": "issues", "href": f"{self.repo}/issues", "type": HTML, "title": "Report a problem"},
            {"rel": "about", "href": self.hosting, "type": HTML, "title": "Hosting page on Source Cooperative"},
        ]

    def header(self, rel_json: str) -> str:
        return (
            f"[Open in data browser]({self.browser_url(rel_json)}) · [Source repository]({self.repo}) · "
            f"[Report a problem]({self.repo}/issues) · [Hosting repository]({self.hosting})"
        )


def docs_links(agents_title: str, readme_title: str) -> list[dict]:
    return [
        {"rel": "describedby", "href": "./README.md", "type": MD, "title": readme_title},
        {"rel": "agents", "href": "./AGENTS.md", "type": MD, "title": agents_title},
    ]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if not path.exists() or path.read_text() != text:
        path.write_text(text)


def write_text(path: Path, text: str) -> None:
    if not path.exists() or path.read_text() != text:
        path.write_text(text)


def data_asset(f: dict | None) -> dict:
    asset = {
        "type": COG,
        "roles": ["data"],
        "title": "Wetland class map (COG)",
        "description": (
            "One band of GWL_FCS30D class codes, uint8, EPSG:4326, about 30 m. The embedded colour "
            "table draws the classes; 255 is ocean and is declared nodata."
        ),
        "data_type": "uint8",
        "nodata": NODATA,
        "classification:classes": classes(),
    }
    if f:
        asset = {"href": f"./{f['item_id']}.tif", **asset,
                 "file:size": f["file:size"], "file:checksum": f["file:checksum"]}
        st = f["statistics"]
        asset["statistics"] = {k: st[k] for k in ("minimum", "maximum", "mean", "stddev", "valid_percent") if k in st}
    return asset


def build_item(f: dict, nav: Nav) -> dict:
    year, tile = f["year"], f["tile"]
    start, end = year_interval(year)
    bbox = clamp_bbox(f["bbox"])
    return {
        "type": "Feature",
        "stac_version": "1.1.0",
        "stac_extensions": [EXT["classification"], EXT["projection"], EXT["file"]],
        "id": f["item_id"],
        "collection": COLLECTION,
        "geometry": polygon(bbox),
        "bbox": bbox,
        "properties": {
            "title": f"Tile {tile}, {year}",
            "datetime": None,
            "start_datetime": start,
            "end_datetime": end,
            "proj:code": f"EPSG:{f['epsg']}",
            "proj:shape": f["shape"],
            "proj:transform": f["transform"],
        },
        "assets": {"data": data_asset(f)},
        "links": [
            {"rel": "root", "href": "../../../../catalog.json", "type": JSON},
            {"rel": "parent", "href": "../catalog.json", "type": JSON},
            {"rel": "collection", "href": "../../../collection.json", "type": JSON},
        ],
    }


def subcatalog(cid: str, title: str, description: str, depth: int, children: list[dict], rel_json: str, nav: Nav) -> dict:
    up = "../" * depth
    return {
        "type": "Catalog",
        "stac_version": "1.1.0",
        "stac_extensions": [PORTOLAN],
        "id": cid,
        "title": title,
        "description": description,
        "updated": MIRRORED,
        "links": [
            {"rel": "root", "href": f"{up}catalog.json", "type": JSON},
            {"rel": "parent", "href": "../collection.json" if depth == 2 else "../catalog.json", "type": JSON},
            *children,
            *docs_links("Agent guide for this catalog", "README for this catalog"),
            *nav.links(rel_json),
        ],
    }


def sub_readme(title: str, rel_json: str, nav: Nav, body: str) -> str:
    return f"# {title}\n\n{nav.header(rel_json)}\n\n{body}\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--facts", required=True, type=Path)
    a = ap.parse_args()
    nav = Nav(load_config())

    facts = [json.loads(p.read_text()) for p in sorted(a.facts.glob("*.json"))]
    if not facts:
        sys.exit(f"no facts in {a.facts}")
    by_year: dict[int, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for f in facts:
        block = f["href"].split("/")[2]
        by_year[f["year"]][block].append(f)

    coll_dir = CATALOG / COLLECTION
    year_links = []
    for year in sorted(by_year):
        ydir = coll_dir / str(year)
        block_links = []
        for block in sorted(by_year[year]):
            bdir = ydir / block
            tiles = sorted(by_year[year][block], key=lambda f: f["tile"])
            item_links = []
            for f in tiles:
                write_json(bdir / f["item_id"] / f"{f['item_id']}.json", build_item(f, nav))
                item_links.append({"rel": "item", "href": f"./{f['item_id']}/{f['item_id']}.json",
                                   "type": GEOJSON, "title": f"Tile {f['tile']}, {year}"})
            btitle = f"GWL_FCS30D {year}, {block_title(block)}"
            rel = f"{COLLECTION}/{year}/{block}/catalog.json"
            w, s, e, n = block_bounds(tiles[0]["tile"])
            write_json(bdir / "catalog.json", subcatalog(
                f"{COLLECTION}-{year}-{block}", btitle,
                f"The {len(tiles)} GWL_FCS30D tiles for {year} in the 20° block {block_title(block)}. "
                f"Each item is one 5° × 5° tile of wetland classes at about 30 m. "
                f"See the [collection agent guide](../../AGENTS.md) for the class codes and queries.",
                3, item_links, rel, nav))
            rows = "\n".join(f"| [{f['tile']}]({f['item_id']}/{f['item_id']}.json) | {f['file:size'] / 1e6:.1f} MB |" for f in tiles)
            write_text(bdir / "README.md", sub_readme(btitle, rel, nav,
                f"GWL_FCS30D wetland classes for {year}, tiles with an upper-left corner in "
                f"{block_title(block)} (bounds {w}, {s}, {e}, {n}). This catalog groups the "
                f"producer's 5° tiles so no catalog lists more than 16 items.\n\n"
                f"Licence: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). "
                f"Source: [GWL_FCS30D on Zenodo]({ZENODO_RECORD}), by Liangyun Liu, Xiao Zhang et al., "
                f"Aerospace Information Research Institute, Chinese Academy of Sciences. "
                f"The [collection README](../../README.md) describes the classes, the conversion and the citation.\n\n"
                f"| Tile | COG size |\n|---|---|\n{rows}"))
            write_text(bdir / "AGENTS.md", sub_readme(f"Agent guide: {btitle}", rel, nav,
                f"This catalog only groups items. Read the [collection agent guide](../../AGENTS.md) "
                f"first: it holds the class codes, the nodata rule and tested queries.\n\n"
                f"Each item here is one tile for {year}. Its `data` asset is a COG at the same path "
                f"with a `.tif` suffix. To query every tile at once, filter the collection's "
                f"`items.parquet` on `start_datetime` and `bbox` instead of walking this tree."))
            block_links.append({"rel": "child", "href": f"./{block}/catalog.json", "type": JSON, "title": block_title(block)})

        ytitle = f"GWL_FCS30D {year}"
        rel = f"{COLLECTION}/{year}/catalog.json"
        n_tiles = sum(len(v) for v in by_year[year].values())
        write_json(ydir / "catalog.json", subcatalog(
            f"{COLLECTION}-{year}", ytitle,
            f"GWL_FCS30D wetland classes for {year}: {n_tiles} tiles of 5° × 5°, grouped in 20° blocks. "
            f"See the [collection agent guide](../AGENTS.md) for the class codes and queries.",
            2, block_links, rel, nav))
        write_text(ydir / "README.md", sub_readme(ytitle, rel, nav,
            f"The GWL_FCS30D wetland map for {year}: {n_tiles} tiles in {len(by_year[year])} blocks of 20°. "
            f"The [collection README](../README.md) describes the classes, the conversion and the citation.\n\n"
            f"Licence: [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Source: "
            f"[GWL_FCS30D on Zenodo]({ZENODO_RECORD}), file `GWL_FCS30_{year}.zip`."))
        write_text(ydir / "AGENTS.md", sub_readme(f"Agent guide: {ytitle}", rel, nav,
            f"This catalog only groups the {year} items by 20° block. Read the "
            f"[collection agent guide](../AGENTS.md) first. To list or query the {year} tiles, filter "
            f"the collection's `items.parquet` on `start_datetime = '{year}-01-01'`."))
        year_links.append({"rel": "child", "href": f"./{year}/catalog.json", "type": JSON, "title": str(year)})

    collection = {
        "type": "Collection",
        "stac_version": "1.1.0",
        "stac_extensions": [PORTOLAN, EXT["classification"], EXT["file"], EXT["scientific"], EXT["projection"]],
        "id": COLLECTION,
        "title": "GWL_FCS30D: global 30 m annual wetland maps, 2000–2022",
        "description": (
            "Annual global maps of eight wetland classes at 30 m for 2000 to 2022, produced from "
            "Landsat time series by Xiao Zhang, Liangyun Liu and colleagues at the Aerospace Information "
            "Research Institute, Chinese Academy of Sciences ([paper](https://doi.org/10.1038/s41597-024-03143-0)). "
            "This mirror converts the producer's yearly zip archives on [Zenodo](https://zenodo.org/records/10068479) "
            "into Cloud-Optimized GeoTIFFs with embedded colour tables, statistics and overviews, one STAC item per "
            "5° tile per year, and an `items.parquet` index of all items. Pixel values are unchanged. Read "
            "[AGENTS.md](AGENTS.md) before you query it."
        ),
        "license": "CC-BY-4.0",
        "keywords": ["wetlands", "GWL_FCS30D", "land cover", "Landsat", "mangrove", "tidal flat",
                     "salt marsh", "swamp", "marsh", "Ramsar", "SDG 6.6.1", "time series", "global"],
        "providers": [
            {"name": "Aerospace Information Research Institute, Chinese Academy of Sciences (Liangyun Liu, Xiao Zhang et al.)",
             "description": "Produced GWL_FCS30D and publishes it on Zenodo.",
             "roles": ["producer", "licensor"], "url": "http://english.aircas.cas.cn/"},
            {"name": "Portolan Mirrors",
             "description": "Maintains this mirror: COG conversion, STAC metadata, item index and documentation.",
             "roles": ["processor", "host"], "url": nav.repo},
        ],
        "extent": {
            "spatial": {"bbox": [clamp_bbox(union(f["bbox"] for f in facts))]},
            "temporal": {"interval": [[year_interval(min(by_year))[0], year_interval(max(by_year))[1]]]},
        },
        "updated": MIRRORED,
        "sci:doi": ZENODO_DOI,
        "sci:citation": DATASET_CITATION,
        "sci:publications": [{"doi": PAPER_DOI, "citation": PAPER_CITATION}],
        "item_assets": {"data": data_asset(None)},
        "assets": {
            "items": {"href": "./items.parquet", "type": "application/vnd.apache.parquet",
                      "roles": ["collection-mirror"], "title": "All items as STAC-GeoParquet",
                      "description": "One row per tile-year item, spatially ordered. Query it instead of walking the tree."},
            "thumbnail": {"href": "./thumbnail.png", "type": "image/png", "roles": ["thumbnail"],
                          "title": "Wetland classes in 2022", "description": "Drawn from the 2022 overview with the embedded colour table."},
            "overview-2022": {"href": "./overview-2022.tif", "type": COG, "roles": ["visual", "overview"],
                              "title": "Global overview, 2022 (RGB, Web Mercator)",
                              "description": "8-bit RGBA mosaic of the 2022 tiles in EPSG:3857, coloured with the class table. "
                                             "For browsing the coverage, not for analysis.",
                              "start_datetime": year_interval(2022)[0], "end_datetime": year_interval(2022)[1]},
            **{
                f"source-{f['key'][-8:-4]}" if f["key"].endswith(".zip") else "source-script": {
                    "href": f"{ZENODO_RECORD}/files/{f['key']}",
                    "type": "application/zip" if f["key"].endswith(".zip") else "text/javascript",
                    "roles": ["source"] if f["key"].endswith(".zip") else ["metadata"],
                    "title": (f"Upstream archive {f['key']} (Zenodo)" if f["key"].endswith(".zip")
                              else "Producer's Earth Engine classification script (Zenodo)"),
                    "description": (f"The producers' original {f['key'][-8:-4]} maps: 957 single-band"
                                    " GeoTIFF tiles, before this mirror's COG conversion. Pixels are identical."
                                    if f["key"].endswith(".zip") else
                                    "The Google Earth Engine script the producers published with the data. It"
                                    " defines the class codes (line 78) and fills unclassified land with 0 (line 88)."),
                    "file:size": f["size"],
                    # sha256 of the download, taken after its Zenodo md5 verified
                    # (tools/download.sh). Omitted until then, never guessed.
                    **({"file:checksum": SOURCE_SHA256[f["key"]]} if f["key"] in SOURCE_SHA256 else {}),
                }
                for f in sorted(ZENODO["files"], key=lambda f: f["key"])
            },
        },
        "links": [
            {"rel": "root", "href": "../catalog.json", "type": JSON},
            {"rel": "parent", "href": "../catalog.json", "type": JSON},
            *year_links,
            *docs_links("Agent guide for GWL_FCS30D", "GWL_FCS30D README"),
            {"rel": "via", "href": ZENODO_RECORD, "type": HTML, "title": "Upstream record on Zenodo"},
            {"rel": "cite-as", "href": f"https://doi.org/{ZENODO_DOI}", "type": HTML, "title": "Dataset DOI"},
            {"rel": "license", "href": "https://creativecommons.org/licenses/by/4.0/", "type": HTML, "title": "CC-BY-4.0"},
            *nav.links(f"{COLLECTION}/collection.json"),
        ],
    }
    staging = (ROOT / load_config()["data_dir"]).resolve() / COLLECTION
    for asset in collection["assets"].values():
        rel = asset["href"].removeprefix("./")
        local = next((d / rel for d in (staging, coll_dir) if (d / rel).exists()), None)
        if not asset["href"].startswith("http") and local:
            asset["file:size"] = local.stat().st_size
            asset["file:checksum"] = "1220" + sha256_file(local)
    write_json(coll_dir / "collection.json", collection)

    root_path = CATALOG / "catalog.json"
    root = json.loads(root_path.read_text())
    keep = [l for l in root["links"] if l["rel"] in ("icon",)]
    root.update({
        "stac_extensions": [PORTOLAN],
        "id": "gwl-fcs30d",
        "title": "GWL_FCS30D global wetland maps (Portolan mirror)",
        "description": (
            "A Portolan mirror of GWL_FCS30D, the annual global 30 m wetland maps for 2000 to 2022 by the "
            "Aerospace Information Research Institute, Chinese Academy of Sciences. The data are "
            "Cloud-Optimized GeoTIFFs with one STAC item per 5° tile per year. Start at [AGENTS.md](AGENTS.md)."
        ),
        "updated": MIRRORED,
        "links": [
            {"rel": "root", "href": "./catalog.json", "type": JSON},
            {"rel": "self", "href": f"{nav.base}/catalog.json", "type": JSON},
            {"rel": "child", "href": f"./{COLLECTION}/collection.json", "type": JSON,
             "title": "GWL_FCS30D: global 30 m annual wetland maps, 2000–2022"},
            *docs_links("Catalog agent guide", "Catalog README"),
            *keep,
            *nav.links("catalog.json"),
        ],
    })
    write_json(root_path, root)
    print(f"{len(facts)} items, {len(by_year)} years, {sum(len(v) for v in by_year.values())} block catalogs")


if __name__ == "__main__":
    main()
