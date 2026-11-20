# GWL_FCS30D global wetland maps (Portolan mirror)

[Open in data browser](https://browser.portolan-sdi.org/#/external/data.source.coop/portolan-mirrors/gwl-fcs30d/catalog.json) · [Source repository](https://github.com/nlebovits/gwl-fcs30d) · [Report a problem](https://github.com/nlebovits/gwl-fcs30d/issues) · [Hosting repository](https://source.coop/portolan-mirrors/gwl-fcs30d)

## What is here

One collection, [GWL_FCS30D](gwl-fcs30d/README.md): annual maps of eight
wetland classes at 30 m for every year from 2000 to 2022, worldwide. Each year
is 957 tiles of 5° × 5°, each a Cloud-Optimized GeoTIFF with an embedded colour
table. Use it to measure wetland extent and change, by class, for any area and
any year in the range, without downloading the 58 GB upstream archive.

The [collection README](gwl-fcs30d/README.md) lists the classes and the
conversion. The [agent guide](AGENTS.md) has queries.

## License

[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/), as stated on the
[Zenodo record](https://zenodo.org/records/10068479). Attribute the producers
and cite the dataset and its paper:

- Liu, L. & Zhang, X. (2023). Time-series global 30 m wetland maps from 2000 to
  2022 [Data set]. Zenodo. <https://doi.org/10.5281/zenodo.10068479>
- Zhang, X., Liu, L., Zhao, T., Wang, J., Liu, W. & Chen, X. Global annual
  wetland dataset at 30 m with a fine classification system from 2000 to 2022.
  Sci Data 11, 310 (2024). <https://doi.org/10.1038/s41597-024-03143-0>

The producers add a request that is not a licence condition: "If you plan to
use our data in a scientific analysis paper, we strongly recommend contacting
us in advance to seek opinions, and consider our contributions in the
acknowledgments or as co-authors."

## Provenance

This catalog is a **mirror**. The data was produced by Liangyun Liu, Xiao
Zhang and colleagues at the Aerospace Information Research Institute, Chinese
Academy of Sciences, and is published on
[Zenodo](https://zenodo.org/records/10068479) as one zip archive per year.
This mirror converted those archives to COGs without changing a pixel, added
STAC metadata and an item index, and is maintained by Portolan Mirrors in the
[source repository](https://github.com/nlebovits/gwl-fcs30d). The upstream
dataset is static. A new Zenodo version would be a new sync.

## Access

Every tile of every year is one row in the collection's `items.parquet`. This
query lists the 2022 tiles that cover the Sundarbans, with their COG URLs,
without downloading anything:

```sql
INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs;
SELECT id, assets.data.href
FROM read_parquet('https://data.source.coop/portolan-mirrors/gwl-fcs30d/gwl-fcs30d/items.parquet')
WHERE start_datetime = TIMESTAMPTZ '2022-01-01 00:00:00+00'
  AND bbox.xmin < 89.9 AND bbox.xmax > 88.8 AND bbox.ymin < 22.4 AND bbox.ymax > 21.5;
```
