# AGENTS.md — GWL_FCS30D global wetland maps

[Open in data browser](https://browser.portolan-sdi.org/#/external/data.source.coop/portolan-mirrors/gwl-fcs30d/catalog.json) · [Source repository](https://github.com/nlebovits/gwl-fcs30d) · [Report a problem](https://github.com/nlebovits/gwl-fcs30d/issues) · [Hosting repository](https://source.coop/portolan-mirrors/gwl-fcs30d)

Guidance for AI agents and automated clients working with this catalog.

**One rule survives every edit to this file.** Every claim here is either quoted
from a source or measured from the data. If you cannot point at where a fact
came from, it does not belong in this file.

## What this catalog holds

The root is `https://data.source.coop/portolan-mirrors/gwl-fcs30d/catalog.json`.
It has one collection, `gwl-fcs30d`: annual 30 m wetland class maps for 2000
to 2022, one COG per 5° tile per year. Read the
[collection agent guide](gwl-fcs30d/AGENTS.md) before you query. It holds the
class codes, the nodata rule, and the tested queries.

## How to read it

Do not walk the STAC tree to find tiles. It has 23 year catalogs, each split
into 20° blocks, and over 22,000 item files. Query
`gwl-fcs30d/items.parquet` instead: one row per item, with `bbox`,
`start_datetime`, and `assets.data.href`. The
[collection agent guide](gwl-fcs30d/AGENTS.md) has the queries.

## Join keys

There is one collection, so nothing joins across collections. Within it, an
item id is `<tile>_<year>`, for example `E100N25_2022`. The same tile code in
two years covers the same pixels on the same grid, so items with the same tile
code stack into a time series.

## Structure

Structural links are relative. The root catalog carries an absolute `self`
link, so a client can resolve every relative href against it.
