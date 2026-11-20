# GWL_FCS30D: global 30 m annual wetland maps, 2000–2022

[Open in data browser](https://browser.portolan-sdi.org/#/external/data.source.coop/portolan-mirrors/gwl-fcs30d/gwl-fcs30d/collection.json) · [Source repository](https://github.com/nlebovits/gwl-fcs30d) · [Report a problem](https://github.com/nlebovits/gwl-fcs30d/issues) · [Hosting repository](https://source.coop/portolan-mirrors/gwl-fcs30d)

GWL_FCS30D maps eight wetland classes worldwide at 30 m, once a year from 2000
to 2022. Xiao Zhang, Liangyun Liu and colleagues at the Aerospace Information
Research Institute, Chinese Academy of Sciences, produced it from Landsat time
series on Google Earth Engine
([paper](https://doi.org/10.1038/s41597-024-03143-0)). The paper reports that
"the GWL_FCS30D maps were found to achieve an overall accuracy and Kappa
coefficient of 86.95 ± 0.44% and 0.822, respectively, in 2020".

This collection is a mirror of the producers' [Zenodo record](https://zenodo.org/records/10068479),
converted to Cloud-Optimized GeoTIFFs. Agents and scripts should start at
[AGENTS.md](AGENTS.md).

## Classes

Each pixel holds one class code. Codes and definitions are from the paper's
"Data Records" section and
[Table 1](https://www.nature.com/articles/s41597-024-03143-0/tables/1).

| Code | Class | Definition | Colour |
|---|---|---|---|
| 0 | Non-wetland | Land the producer did not classify as wetland | `#EBEBEB` |
| 180 | Permanent water | Retaining water consistently throughout the year | `#0046C8` |
| 181 | Swamp | Inland natural wetlands mainly covered by tree vegetation (forest and shrub) | `#00A884` |
| 182 | Marsh | Inland natural wetlands dominated by herbaceous vegetation | `#73FFDF` |
| 183 | Flooded flat | Non-vegetated inland areas regularly inundated with water, typically during seasonal or periodic flooding events | `#9EBBD7` |
| 184 | Saline | High salt concentrations in the area's water, soil, or vegetation | `#828282` |
| 185 | Mangrove forest | Salt-tolerant trees and shrubs that grow in brackish water | `#F57AB6` |
| 186 | Salt marsh | Coastal wetland characterized by salt-tolerant vegetation, typically found in intertidal zones | `#66CDAB` |
| 187 | Tidal flat | Muddy or rocky areas that are submerged during high tides and exposed during low tides | `#444F89` |
| 188 | Undocumented code 188 | Present in the files, absent from the producers' code list. See [Known issues](#known-issues) | `#FF00FF` |
| 255 | Ocean | Outside the mapped area. Nodata in this mirror, drawn transparent | none |

The colours for 181 to 187 are the producers' own, from the legend of their
sibling product GLC_FCS30D, which uses the same codes
([user guide](https://zenodo.org/records/15063683)). The producers publish no
colours for GWL_FCS30D itself. 180 takes the colour of GLC_FCS30D's "Water body"
class. The grey for 0 and the magenta for 188 are this mirror's choices.

## What is in the collection

- **One item per tile per year.** 957 tiles of 5° × 5° for each of the 23
  years. An item's id is `<tile>_<year>`, for example `E100N25_2022`. The tile
  code names the tile's upper-left corner, as the producers name their files.
- **One COG per item.** Single band, uint8, EPSG:4326, 0.000269494585235856°
  per pixel (about 30 m at the equator). ZSTD compression, 512 px internal
  tiles, internal overviews built with `mode` resampling, embedded band
  statistics, an embedded colour table, and nodata 255.
- **`items.parquet`.** Every item as one row of STAC-GeoParquet, so a client can
  find tiles by place and year in one query.
- **`overview-2022.tif`.** An RGBA mosaic of 2022 in Web Mercator at about
  1.2 km per pixel, for seeing the coverage at a glance. Not for analysis.
- **Links to the upstream originals.** The 23 yearly zip archives on Zenodo, as
  `source` assets, and the producers' Earth Engine script.

The STAC tree groups items by year, then by 20° block, so no catalog lists more
than 16 items.

## License and citation

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/), as stated on the
Zenodo record. Cite both:

- Liu, L. & Zhang, X. (2023). Time-series global 30 m wetland maps from 2000 to
  2022 [Data set]. Zenodo. <https://doi.org/10.5281/zenodo.10068479>
- Zhang, X., Liu, L., Zhao, T., Wang, J., Liu, W. & Chen, X. Global annual
  wetland dataset at 30 m with a fine classification system from 2000 to 2022.
  Sci Data 11, 310 (2024). <https://doi.org/10.1038/s41597-024-03143-0>

The Zenodo record also makes a request, which is not a licence condition: "If
you plan to use our data in a scientific analysis paper, we strongly recommend
contacting us in advance to seek opinions, and consider our contributions in
the acknowledgments or as co-authors."

## Provenance

Source: [Zenodo record 10068479](https://zenodo.org/records/10068479),
published 2023-11-03, 23 zip archives (`GWL_FCS30_2000.zip` to
`GWL_FCS30_2022.zip`) and one Earth Engine script.

What this mirror did, with the code in the
[source repository](https://github.com/nlebovits/gwl-fcs30d/tree/main/tools):

1. Downloaded every archive and checked it against the MD5 that Zenodo lists.
2. Converted each GeoTIFF inside to a COG with GDAL 3.12 (`tools/convert.py`).
   The pixel values and the grid are unchanged. The conversion reads every
   output back and compares it with its source, block by block. It adds 255 as
   the nodata value and the colour table above. The upstream files declare
   neither.
3. Wrote the STAC metadata (`tools/build_stac.py`), the item index
   (`tools/build_items_parquet.py`) and the 2022 overview
   (`tools/build_overview.py`).

The dataset is static upstream. A new Zenodo version would need a new sync.

## Known issues

- **The Zenodo description does not match the files.** It says "961 5°×5°
  geographical tiles, and each tile contains 23 bands". The published archives
  hold one single-band file per tile per year, and each year has 957 tiles.
  This mirror follows the files.
- **Adjacent tiles overlap.** Each tile is 18,554 pixels wide and high, which is
  5.0002°. Five degrees is 18,553.25 pixels, so neighbouring tiles overlap by
  about three quarters of a pixel and their pixel grids are offset. Pixels in
  the overlap count twice if you sum areas across tiles.
- **Pixel area varies with latitude.** The grid is in degrees. A pixel covers
  about 30 m × 30 m × cos(latitude). Weight by latitude when you compute area.
- **0 is a class, not missing data.** Only 255 is nodata. Excluding 0 drops all
  non-wetland land from a denominator.
- **Code 188 is undocumented.** The producers list codes 0, 180 to 187 and
  255. The files also hold 188, in three tiles, counted over all 22,011 files:

  | Tile | Where | Years | Pixels coded 188 |
  |---|---|---|---|
  | `E55N65` | Russia, 55–60°E, 60–65°N | all 23 | 2,460,586 |
  | `E55S20` | Réunion | all 23 | 670 |
  | `W55N75` | Greenland | 2011 only | 2 |

  This mirror keeps the pixels as they are and labels the code "Undocumented
  code 188". Its meaning is unknown. `classification:classes` lists it like
  any other class.
- **Tile `E55N65_2000` holds pixels coded 185, mangrove forest, at about 65°N.**
  Measured beside the 188 pixels above. Treat class codes near 188 pixels with
  care.
- **Colours for 0, 180 and 188 are not the producers'.** See [Classes](#classes).
