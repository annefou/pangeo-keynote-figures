# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.0
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # 02 — Onto the grid: every source on WGS84 NESTED HEALPix
#
# Each source keeps its own resolution, and lands on the HEALPix depth that matches it
# (healpix-geo, WGS84 ellipsoid, NESTED ordering):
#
# | source | native | HEALPix depth | cell |
# |---|---|---|---|
# | GBIF plant records | points | 16 | ~100 m |
# | Sentinel-2 L2A | 10 m | 18 | ~25 m |
# | Sentinel-3 OLCI | ~300 m | 14 | ~400 m |
#
# Output: `results/montseny_healpix.zarr`, one group per source and depth, following the
# zarr-conventions **dggs** v1 convention with a CF `healpix` grid mapping (as healpix-convert writes it).

# %%
import sys
from pathlib import Path

# shared settings and helpers live in notebooks/lib/ (works from the repo root and from notebooks/)
sys.path.insert(0, str(next(p for p in (Path.cwd() / "lib", Path.cwd() / "notebooks" / "lib") if p.exists())))
import json

import numpy as np
import xarray as xr

from config import RAW, RESULTS, DEPTH_GROUND, DEPTH_S2, DEPTH_S3
from healpix_tools import utm_lonlat, cell_ids, cell_means, dggs_dataset

RESULTS.mkdir(parents=True, exist_ok=True)
STORE = RESULTS / "montseny_healpix.zarr"

# %% [markdown]
# ## Sentinel-2, 10 m pixels to depth-18 cells (mean surface reflectance)

# %%
s2 = xr.open_dataset(RAW / "s2_montseny_r10m.nc")
lon, lat = utm_lonlat(s2.x.values, s2.y.values)
rgb = np.stack([s2.b04.values, s2.b03.values, s2.b02.values], -1).astype("float32")
u18, m18, n18 = cell_means(rgb, cell_ids(lon, lat, DEPTH_S2))
dggs_dataset(DEPTH_S2, u18, {"b04": m18[:, 0], "b03": m18[:, 1], "b02": m18[:, 2], "n_pixels": n18},
             source="Copernicus Sentinel-2 L2A 2026-09-15, 10 m, cell means").to_zarr(
    STORE, group=f"sentinel2/{DEPTH_S2}", mode="w", zarr_format=3)
print(len(u18), "depth-18 cells")

# %% [markdown]
# ## Sentinel-3 OLCI pixels to depth-14 cells (mean top-of-atmosphere radiance)

# %%
s3 = xr.open_dataset(RAW / "s3_montseny_olci.nc")
ids3 = cell_ids(s3.longitude.values, s3.latitude.values, DEPTH_S3)
rad = np.stack([s3.oa08_radiance.values, s3.oa06_radiance.values, s3.oa04_radiance.values], -1)
u3, m3, n3 = cell_means(rad, ids3)
dggs_dataset(DEPTH_S3, u3, {"oa08_radiance": m3[:, 0], "oa06_radiance": m3[:, 1], "oa04_radiance": m3[:, 2],
                            "n_pixels": n3},
             source="Copernicus Sentinel-3 OLCI L1 EFR 2026-09-15, cell means").to_zarr(
    STORE, group=f"sentinel3/{DEPTH_S3}", mode="a", zarr_format=3)
print(len(u3), "depth-14 cells")

# %% [markdown]
# ## GBIF plant records: count per cell, at the ground depth (16) and at the bridge depth (14)

# %%
g = json.loads((RAW / "gbif_montseny.json").read_text())["records"]
glon = np.array([r["decimalLongitude"] for r in g]); glat = np.array([r["decimalLatitude"] for r in g])
for d in sorted({DEPTH_GROUND, DEPTH_S3}, reverse=True):
    u, c = np.unique(cell_ids(glon, glat, d), return_counts=True)
    dggs_dataset(d, u, {"n_records": c}, source="GBIF.org plant records 2025-2026 via healpix-connector").to_zarr(
        STORE, group=f"gbif/{d}", mode="a", zarr_format=3)
    print(d, len(u), "cells with records")
