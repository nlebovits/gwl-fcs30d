# gwl-fcs30d

The git-backed [Portolan](https://www.portolan-sdi.org/) catalog that mirrors
**GWL_FCS30D**, the annual global 30 m wetland maps for 2000 to 2022 by the
Aerospace Information Research Institute, Chinese Academy of Sciences
([paper](https://doi.org/10.1038/s41597-024-03143-0),
[Zenodo](https://zenodo.org/records/10068479)). Proposed in
[portolan-data#67](https://github.com/portolan-sdi/portolan-data/issues/67).

The published catalog lives at
**[source.coop/portolan-mirrors/gwl-fcs30d](https://source.coop/portolan-mirrors/gwl-fcs30d)**.

Upstream publishes 23 zip archives of plain GeoTIFFs. This mirror hosts them as
22,011 Cloud-Optimized GeoTIFFs, one per 5° tile per year, with embedded colour
tables and statistics. It adds STAC metadata with the classification extension,
an `items.parquet` index of every item, a 2022 overview, and documentation.

## Layout

- `catalog/` — the published catalog. Everything in it is published, nothing
  outside it ever is.
- `tools/` — the build: `convert.py` (zip to COG), `build_stac.py` (the STAC
  tree), `build_items_parquet.py`, `build_overview.py`, and the template's
  `publish.py` and `upload_data.py`. `gwl.py` holds the class table and its
  sources.
- `docs/research/` — the Zenodo record and the producers' Earth Engine script,
  as fetched.
- `RUNBOOK.md` — the build, step by step.

## Contributing

Corrections are welcome as pull requests. CI validates every change with
[rashid](https://pypi.org/project/rashid/). Problems with the data itself
belong with the producers. The
[issue tracker](https://github.com/nlebovits/gwl-fcs30d/issues) here covers
the catalog, its metadata and the conversion.

## License

Catalog metadata and tooling: see `LICENSE`. The GWL_FCS30D data is
[CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). Cite the dataset and
the paper, as the [collection README](catalog/gwl-fcs30d/README.md) shows.
