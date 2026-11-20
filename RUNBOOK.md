# Runbook

The full build, from the Zenodo record to the published catalog. Paths assume
this repository at `~/gwl-fcs30d` and the data directory at
`~/gwl-fcs30d-data` beside it. The data directory is never in git.

Every heavy step runs in a memory-capped systemd unit, so a runaway job is
killed instead of the host. Peak measured on 2026-11-20: about 350 MB per
conversion worker.

## 1. Download and verify

`tools/download.sh` downloads every file in the record with resumable `curl`,
checks each against the MD5 Zenodo lists, then writes
`docs/research/zenodo-10068479-sha256.json` for the `source` assets.

```bash
systemd-run --user --wait --unit=gwl-download -p MemoryMax=2G \
  ~/gwl-fcs30d/tools/download.sh
```

58.3 GB in all. Zenodo's throughput sets the pace.

## 2. Convert to COG

`tools/convert_as_ready.sh` converts each year as soon as its zip is complete,
so conversion overlaps the download:

```bash
systemd-run --user --wait --unit=gwl-convert -p MemoryMax=24G -p MemorySwapMax=0 \
  --setenv=PATH="$PATH" ~/gwl-fcs30d/tools/convert_as_ready.sh
```

Each `tools/convert.py` run skips tiles already converted, so a rerun resumes.
Read progress with `journalctl --user -u gwl-convert -f`. A tile with a value
outside the class table in `tools/gwl.py` fails, and its year is reported.

## 3. Build the overview, the STAC tree and the item index

```bash
systemd-run --user --wait --unit=gwl-overview -p MemoryMax=24G -p MemorySwapMax=0 \
  --working-directory=$PWD --setenv=PATH="$PATH" \
  uv run --with rasterio --with numpy --with pillow python -I tools/build_overview.py \
    --staging ../gwl-fcs30d-data/staging --year 2022
python3 tools/build_stac.py --facts ../gwl-fcs30d-data/facts
uv run --with stac-geoparquet --with geoparquet-io python -I tools/build_items_parquet.py
python3 tools/build_stac.py --facts ../gwl-fcs30d-data/facts   # records the parquet's size and checksum
```

Set `MIRRORED` in `tools/gwl.py` to the time of the download before step 3.

## 4. Check

```bash
python3 tests/run_all.py
rashid check --schema --data-scope local <a copy of catalog/ with the staged data laid in>
```

`--data-scope local` keeps rashid from downloading the 58 GB of Zenodo
`source` assets to check their checksums.

## 5. Publish

Needs the `source-coop` AWS profile from
<https://docs.source.coop/upload-with-the-cli> and a fresh `source-coop login`.

```bash
python3 tools/upload_data.py            # dry run
python3 tools/upload_data.py --confirm  # COGs, items.parquet, overview
python3 tools/publish.py                # dry run
python3 tools/publish.py --confirm      # STAC, README, AGENTS, thumbnail
rashid check --live https://data.source.coop/portolan-mirrors/gwl-fcs30d/catalog.json
```

Upload the data before the metadata, so no published link points at a missing
object.
