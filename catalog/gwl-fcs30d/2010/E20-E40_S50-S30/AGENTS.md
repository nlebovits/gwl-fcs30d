# Agent guide: GWL_FCS30D 2010, 20°E–40°E, 50°S–30°S

[Open in data browser](https://browser.portolan-sdi.org/#/external/data.source.coop/portolan-mirrors/gwl-fcs30d/gwl-fcs30d/2010/E20-E40_S50-S30/catalog.json) · [Source repository](https://github.com/nlebovits/gwl-fcs30d) · [Report a problem](https://github.com/nlebovits/gwl-fcs30d/issues) · [Hosting repository](https://source.coop/portolan-mirrors/gwl-fcs30d)

This catalog only groups items. Read the [collection agent guide](../../AGENTS.md) first: it holds the class codes, the nodata rule and tested queries.

Each item here is one tile for 2010. Its `data` asset is a COG at the same path with a `.tif` suffix. To query every tile at once, filter the collection's `items.parquet` on `start_datetime` and `bbox` instead of walking this tree.
