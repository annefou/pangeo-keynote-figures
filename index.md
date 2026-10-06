# pangeo-keynote-figures

[![CI](https://github.com/annefou/pangeo-keynote-figures/actions/workflows/ci.yml/badge.svg)](https://github.com/annefou/pangeo-keynote-figures/actions/workflows/ci.yml)
[![Jupyter Book](https://github.com/annefou/pangeo-keynote-figures/actions/workflows/jupyter-book.yml/badge.svg)](https://annefou.github.io/pangeo-keynote-figures/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![RO-Crate](https://img.shields.io/badge/RO--Crate-1.2-orange)](ro-crate-metadata.json)

Code and data behind the Earth-observation figures of the keynote **"Pangeo: Openness for Sovereignty, Innovation,
and Sustainable Communities"** (Anne Fouilloux, LifeWatch ERIC; OpenEarthMonitor final event, CREAF, 7 October 2026).
Built from the [FORRT replication template](https://github.com/ScienceLiveHub/forrt-replication-template): one Snakemake
workflow, four jupytext notebooks, a pinned pixi environment, Docker, RO-Crate and GitHub Actions.

Everything is read from its source on each run, with open tools only: Copernicus Sentinel-2 and Sentinel-3 from
**ESA's EOPF Sample Service** (Zarr, opened lazily with `xr.open_datatree`), GBIF records through
[healpix-connector](https://github.com/annefou/healpix-connector), and every source placed on **WGS84 NESTED HEALPix**
cells with [healpix-geo](https://github.com/GRID4EARTH/healpix-geo) (GRID4EARTH). Intermediate HEALPix data are written as
Zarr v3 following the [zarr-conventions/dggs](https://github.com/zarr-conventions/dggs) convention with a CF `healpix`
grid mapping, as [healpix-convert](https://github.com/GRID4EARTH/healpix-convert) writes them.

| Slide | Figure | Output | Data | Re-run check |
|---|---|---|---|---|
| 1 (cover) | Copernicus Sentinel-2, 15 Sep 2026: the Vallès, Montseny and the Maresme coast | `figures/catalonia_cover.jpg` | Sentinel-2 L2A T31TDG + T31TDF, 20 m, EOPF Zarr | **byte-identical** to the deck image (2026-10-06) |
| 2 | The same scene as a band | `figures/catalonia_band.jpg` | same | **byte-identical** |
| 9 | From the ground to space: GBIF plant records (depth 16, ~100 m), Sentinel-2 (depth 18, ~25 m), Sentinel-3 OLCI (depth 14, ~400 m), and the bridge (5 km zoom): each record on the HEALPix cell matching its stated uncertainty (25 m to 6 km), Sentinel-2 read on that same cell | `figures/bridge_strip.jpg`, `figures/panel*.png`, `results/montseny_healpix.zarr`, `results/records_support.csv`, `results/summary.csv` | Sentinel-2 L2A T31TDG 10 m; Sentinel-3 OLCI L1 EFR; GBIF plants 2025–2026 | the deck uses this output (2026-10-06); GBIF records retrieved 2026-10-06T07:11Z |
| 8 | The HEALPix grid on WGS84 (globes) | `figures/slide8_healpix_globes.png` | re-run of [esa-frontiers-figures](https://github.com/annefou/esa-frontiers-figures) `sphere-vs-ellipsoid` at a pinned commit (step 06) | **pixel-identical** (`results/upstream_check.json`) |
| 10 | BIOMASS forest height × GBIF, Beni | `figures/slide10_beni_biomass_gbif.png` | re-run of `beni-biomass-forest-height/plot_fh3.py` from the upstream per-cell results (step 06); the full BIOMASS pipeline needs an ESA MAAP account and is documented upstream | **pixel-identical** |

Photos on slide 9 (drone, eDNA, LiDAR) are third-party images, credited in DATA_LICENSES.md; they are not
produced here.

## Quick start

```bash
git clone https://github.com/annefou/pangeo-keynote-figures.git
cd pangeo-keynote-figures
pixi install
pixi run snakemake --cores 1
```

No credentials are needed. The four steps:

1. `notebooks/01_data_download.py` — Sentinel-2 / Sentinel-3 windows from EOPF Zarr; GBIF records via healpix-connector.
2. `notebooks/02_data_clean.py` — every source onto its own HEALPix depth (dggs-convention Zarr).
3. `notebooks/03_analysis.py` — the bridge: each GBIF record on the cell matching its uncertainty (finest depth whose
   cell edge is at least twice the stated uncertainty, depth 6–18), Sentinel-2 read on that cell; records without a
   stated uncertainty (290 of 861) are left out, not guessed. `results/records_support.csv`, `results/summary.csv`.
4. `notebooks/04_figures.py` — the images used in the deck. Markers are colour-blind safe (cyan and white,
   with a black halo).
5. `notebooks/05_photos.py` — the three third-party photos of slide 9 (drone, eDNA, LiDAR) from Wikimedia Commons,
   with author, licence and source read from the Commons API into `figures/photo_credits.json`.
6. `notebooks/06_upstream_figures.py` — slides 8 and 10, re-run from esa-frontiers-figures at a pinned commit, checked
   pixel-identical to the figures used in the deck (matplotlib pinned to 3.11.2 for that).

Products, areas and depths are set in one place: `notebooks/config.py`.

## Known limitations

1. GBIF grows every day: a re-run returns more records than the 861 plant records retrieved on 2026-10-06T07:11Z for
   the slide (the query is in `data/raw/sources.json`). A GBIF download DOI would pin them.
2. The EOPF Sample Service is a preview service; product URLs may move when ESA moves to operational EOPF products.
3. Sentinel-3 OLCI radiance is scaled to the Sentinel-2 reflectance of the same cells (per-band median ratio) **for
   display only**, so that the panels differ by resolution, not by colour. The stored values are unscaled.
4. Tile T31TDF lies at the swath edge of relative orbit 8; it only fills the rows below T31TDG.

## Licence

Code: MIT. Data: see DATA_LICENSES.md. Cite with [CITATION.cff](CITATION.cff).
