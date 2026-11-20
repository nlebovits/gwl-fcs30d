"""Facts about GWL_FCS30D shared by the conversion and the STAC generator.

Every value here has a source, recorded beside it. Change a value only with a
new source.
"""
from __future__ import annotations

import math
import re

# Class codes: Zhang et al. 2024, Scientific Data 11:310, "Data Records"
# (https://doi.org/10.1038/s41597-024-03143-0): "the permanent water, swamp,
# marsh, flooded flat, saline, mangrove, salt marsh, and tidal flat are marked
# as 180, 181, 182, 183, 184, 185, 186, and 187, respectively; the non-wetland
# and ocean are labeled as 0 and 255, respectively."
#
# Descriptions of 180-187: Table 1 of the same paper
# (https://www.nature.com/articles/s41597-024-03143-0/tables/1), verbatim except
# a typographic apostrophe. 0 and 255 are described from the "Data Records"
# quote above and the producer's script (docs/research/, line 88: unmask(0)).
#
# Colours: 181-187 are the producer's own colours for the same codes in the
# GLC_FCS30D user guide (https://zenodo.org/records/15063683, "GLC_FCS30D
# UserGuides.pdf"). 180 takes that legend's "Water body" (210) colour. The
# producer publishes no colour for 0 in this product; the light grey is this
# mirror's choice, so land reads against transparent ocean. 255 is the mirror's
# declared nodata and renders transparent.
CLASSES: dict[int, dict] = {
    0: {"name": "non-wetland", "title": "Non-wetland", "rgb": (235, 235, 235),
        "description": "Land the producer did not classify as wetland (the classifier's unmask(0) fill)."},
    180: {"name": "permanent-water", "title": "Permanent water", "rgb": (0, 70, 200),
          "description": "Retaining water consistently throughout the year"},
    181: {"name": "swamp", "title": "Swamp", "rgb": (0, 168, 132),
          "description": "Inland natural wetlands mainly covered by tree vegetation (forest and shrub)"},
    182: {"name": "marsh", "title": "Marsh", "rgb": (115, 255, 223),
          "description": "Inland natural wetlands dominated by herbaceous vegetation"},
    183: {"name": "flooded-flat", "title": "Flooded flat", "rgb": (158, 187, 215),
          "description": "Non-vegetated inland areas regularly inundated with water, typically during seasonal or periodic flooding events"},
    184: {"name": "saline", "title": "Saline", "rgb": (130, 130, 130),
          "description": "High salt concentrations in the area's water, soil, or vegetation"},
    185: {"name": "mangrove", "title": "Mangrove forest", "rgb": (245, 122, 182),
          "description": "Salt-tolerant trees and shrubs that grow in brackish water"},
    186: {"name": "salt-marsh", "title": "Salt marsh", "rgb": (102, 205, 171),
          "description": "Coastal wetland characterized by salt-tolerant vegetation, typically found in intertidal zones"},
    187: {"name": "tidal-flat", "title": "Tidal flat", "rgb": (68, 79, 137),
          "description": "Muddy or rocky areas that are submerged during high tides and exposed during low tides"},
    # Not in the producer's code list, the paper or their script, but present in
    # the files (first found in 2000: tiles E55N65 and E55S20). Kept unchanged,
    # since a mirror does not rewrite pixels. The magenta is this mirror's
    # choice, picked to stand out.
    188: {"name": "undocumented-188", "title": "Undocumented code 188", "rgb": (255, 0, 255),
          "description": "Present in the producer's files but absent from their published code list. Meaning unknown."},
    255: {"name": "ocean", "title": "Ocean (not mapped)", "rgb": (255, 255, 255),
          "description": "Ocean, outside the mapped area. Declared nodata in this mirror."},
}
NODATA = 255

YEARS = range(2000, 2023)

# When this mirror last copied the upstream record (PORTO-CORE-057). Set it at
# each sync; the generator writes it to `updated` on every catalog and
# collection, so a rerun without a sync changes nothing.
MIRRORED = "2026-11-20T11:42:50Z"  # when the last Zenodo file finished downloading (MD5-verified)

ZENODO_RECORD = "https://zenodo.org/records/10068479"
ZENODO_DOI = "10.5281/zenodo.10068479"
PAPER_DOI = "10.1038/s41597-024-03143-0"
PAPER_CITATION = (
    "Zhang, X., Liu, L., Zhao, T., Wang, J., Liu, W. & Chen, X. Global annual wetland dataset "
    "at 30 m with a fine classification system from 2000 to 2022. Sci Data 11, 310 (2024). "
    "https://doi.org/10.1038/s41597-024-03143-0"
)
DATASET_CITATION = (
    "Liu, L. & Zhang, X. (2023). Time-series global 30 m wetland maps from 2000 to 2022 "
    "[Data set]. Zenodo. https://doi.org/10.5281/zenodo.10068479"
)
BLOCK_DEG = 20  # 20 deg blocks hold at most 16 of the producer's 5 deg tiles (PORTO-CORE-078)

_TILE = re.compile(r"^([EW])(\d+)([NS])(\d+)$")


def tile_corner(tile: str) -> tuple[int, int]:
    """Upper-left corner (lon, lat) of a producer tile code such as E100N25."""
    m = _TILE.match(tile)
    if not m:
        raise ValueError(f"not a GWL tile code: {tile!r}")
    ew, lon, ns, lat = m.groups()
    return (int(lon) if ew == "E" else -int(lon)), (int(lat) if ns == "N" else -int(lat))


def _fmt(v: int, pos: str, neg: str) -> str:
    return f"{pos if v >= 0 else neg}{abs(v)}"


def block_bounds(tile: str) -> tuple[int, int, int, int]:
    lon, top = tile_corner(tile)
    west = math.floor((lon + 180) / BLOCK_DEG) * BLOCK_DEG - 180
    north = 90 - math.floor((90 - top) / BLOCK_DEG) * BLOCK_DEG
    return west, north - BLOCK_DEG, west + BLOCK_DEG, north


def block_of(tile: str) -> str:
    """Directory name of the 20 deg block holding a tile, e.g. E100-E120_N10-N30."""
    w, s, e, n = block_bounds(tile)
    return f"{_fmt(w, 'E', 'W')}-{_fmt(e, 'E', 'W')}_{_fmt(s, 'N', 'S')}-{_fmt(n, 'N', 'S')}"


def block_title(block: str) -> str:
    def deg(t: str) -> str:
        return f"{t[1:]}°{t[0]}"
    lon, lat = block.split("_")
    (w, e), (s, n) = lon.split("-"), lat.split("-")
    return f"{deg(w)}–{deg(e)}, {deg(s)}–{deg(n)}"


def item_id(tile: str, year: int) -> str:
    return f"{tile}_{year}"


if __name__ == "__main__":
    # Self-check: a tile at a block's upper-left, one inside, and the southern/western hemispheres.
    assert block_of("E100N25") == "E100-E120_N10-N30", block_of("E100N25")
    assert block_of("E115N15") == "E100-E120_N10-N30"
    assert block_of("E100N10") == "E100-E120_S10-N10"
    assert block_of("W180N90") == "W180-W160_N70-N90"
    assert block_of("W5S50") == "W20-E0_S70-S50", block_of("W5S50")
    assert tile_corner("W5S50") == (-5, -50)
    assert block_title("E100-E120_N10-N30") == "100°E–120°E, 10°N–30°N"
    print("ok")
