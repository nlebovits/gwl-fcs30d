
## This Repository

The git-backed Portolan mirror of GWL_FCS30D, published at
`s3://portolan-mirrors/gwl-fcs30d/`. Metadata lives here. The COGs, the item
index and the overview are built from the upstream Zenodo archives into
`../gwl-fcs30d-data/staging` and uploaded with `tools/upload_data.py`.
`RUNBOOK.md` has the build order.

### Memory on the build host

Run `tools/convert.py` and `tools/build_overview.py` inside a memory-capped
unit, as `RUNBOOK.md` shows. A full-tile array is 344 MB, and GDAL's default
block cache is 5% of RAM per process. Uncapped, 48 workers took the host down
twice. The tools now stream by block, cap `GDAL_CACHEMAX`, and default to 16
workers. Do not raise the worker count without measuring the peak first.

### Publishing

This catalog publishes with `tools/publish.py` and `tools/upload_data.py`,
never `portolan push`. The two do not interoperate.

### The publish boundary

`catalog/` is the published catalog. Everything in it is published, and
nothing outside it ever is. Do not move a file into `catalog/` to make it
publish, and do not add a path outside `publish_dir` to `tools/publish.py`.
The boundary is the only thing standing between a scratch file and a public
bucket, and it holds because it is structural rather than a list of
exclusions.

### Data never enters git

Never commit a GeoParquet, COG, PMTiles, Zarr, or COPC file. If a gate needs
bytes to check, generate them in CI. Git keeps every version of a binary
forever and deleting it later reclaims nothing.

### The conformance allow-list

`ACCEPTED` in `tests/test_conformance.py` ships empty. Never add an entry
without a matching row in `docs/conformance.md` giving the rule, where it
fires, why it is accepted, and the issue tracking its removal.

### Published agent guides

Every claim in a `catalog/**/AGENTS.md` is either quoted from a source or
measured from the data. An invented join key or column name produces a
confident wrong answer that nothing downstream catches.

### The links back to this repository

`tools/build_stac.py` writes `vcs`, `issues`, `about` and the data-browser
`alternate` link on every catalog and collection, from the keys in
`catalog.publish.yaml`. The Portolan spec recommends `vcs` and `issues` for a
git-backed catalog. See
[git-backed catalogs](https://github.com/portolan-sdi/portolan-spec/blob/main/specs/best-practices/git-backed-catalogs.md).

Keep these hrefs absolute. The repository sits outside the published catalog,
so a relative href resolves against the public base URL.
