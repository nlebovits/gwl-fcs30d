# Agent guide: GWL_FCS30D 2010, 100°E–120°E, 10°N–30°N

[Open in data browser](https://browser.portolan-sdi.org/#/external/data.source.coop/portolan-mirrors/gwl-fcs30d/gwl-fcs30d/2010/E100-E120_N10-N30/catalog.json) · [Source repository](https://github.com/nlebovits/gwl-fcs30d) · [Report a problem](https://github.com/nlebovits/gwl-fcs30d/issues) · [Hosting repository](https://source.coop/portolan-mirrors/gwl-fcs30d)

This catalog only groups items. Read the [collection agent guide](../../AGENTS.md) first: it holds the class codes, the nodata rule and tested queries.

Each item here is one tile for 2010. Its `data` asset is a COG at the same path with a `.tif` suffix. To query every tile at once, filter the collection's `items.parquet` on `start_datetime` and `bbox` instead of walking this tree.
