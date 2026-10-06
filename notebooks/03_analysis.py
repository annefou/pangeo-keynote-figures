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
# # 03 — The bridge: each record on the cell that matches its own uncertainty
#
# A GBIF record is a point *with an uncertainty*: here from 3 m (a phone GPS) to 28 km (a locality name).
# On a nested grid, each record can sit on the cell whose size matches that uncertainty, and the satellite
# data can be read **on that same cell**: Sentinel-2 averaged over a ~25 m cell for a precise record, over a
# ~6 km cell for a vague one. Same cell IDs at every depth, so nothing is regridded per record.
#
# Rule: the finest depth whose cell edge is at least twice the stated uncertainty (the uncertainty is a
# radius), between depth 6 (~100 km) and depth 18 (~25 m). Records without a stated uncertainty are kept
# apart: their support is unknown, and we do not guess it.
#
# Output: `results/records_support.csv` (one row per record: depth, cell, Sentinel-2 on that cell) and
# `results/summary.csv`.

# %%
import json

import numpy as np
import pandas as pd
import xarray as xr

from config import RAW, RESULTS
from healpix_tools import utm_lonlat, cell_ids, cell_means, lookup

EDGE0 = 6_519_000.0   # m, edge of a depth-0 cell: sqrt(4 pi R^2 / 12), mean Earth radius
DMIN, DMAX = 6, 18


def edge(depth):
    return EDGE0 / 2 ** depth


def support_depth(uncertainty_m):
    d = np.floor(np.log2(EDGE0 / (2 * np.asarray(uncertainty_m, float))))
    return np.clip(d, DMIN, DMAX).astype(int)


# %%
g = pd.DataFrame(json.loads((RAW / "gbif_montseny.json").read_text())["records"])
g = g.rename(columns={"coordinateUncertaintyInMeters": "uncertainty_m"})
known = g.dropna(subset=["uncertainty_m"]).copy()
known["depth"] = support_depth(known.uncertainty_m)
known["cell_id"] = np.zeros(len(known), dtype="uint64")
for d in sorted(known.depth.unique()):
    i = known.depth == d
    known.loc[i, "cell_id"] = cell_ids(known.loc[i, "decimalLongitude"].values,
                                       known.loc[i, "decimalLatitude"].values, d)
known["cell_edge_m"] = edge(known.depth).round(1)

# %% [markdown]
# Sentinel-2 on each record's own cell: the mean reflectance of the 10 m pixels inside it, and the share of the
# cell that lies inside the 15 km box (large cells reach beyond it).

# %%
s2 = xr.open_dataset(RAW / "s2_montseny_r10m.nc")
lon, lat = utm_lonlat(s2.x.values, s2.y.values)
rgb = np.stack([s2.b04.values, s2.b03.values, s2.b02.values], -1).astype("float32")
cols = {"s2_b04": [], "s2_b03": [], "s2_b02": [], "n_pixels": []}
vals = np.full((len(known), 4), np.nan)
for d in sorted(known.depth.unique()):
    u, m, n = cell_means(rgb, cell_ids(lon, lat, d))
    i = np.where(known.depth.values == d)[0]
    vals[i] = lookup(u, np.column_stack([m, n]), known.cell_id.values[i].astype("uint64"))
known[["s2_b04", "s2_b03", "s2_b02", "n_pixels"]] = vals
known["share_in_box"] = (known.n_pixels * 100.0 / known.cell_edge_m ** 2).clip(upper=1).round(3)
known.to_csv(RESULTS / "records_support.csv", index=False)
known.groupby("depth").agg(records=("gbifID", "size"), edge_m=("cell_edge_m", "first"))

# %%
summary = pd.DataFrame([{
    "records": len(g), "with_uncertainty": len(known), "without_uncertainty": len(g) - len(known),
    "uncertainty_min_m": known.uncertainty_m.min(), "uncertainty_median_m": known.uncertainty_m.median(),
    "uncertainty_max_m": known.uncertainty_m.max(), "depths_used": known.depth.nunique(),
    "finest_depth": known.depth.max(), "coarsest_depth": known.depth.min()}])
summary.to_csv(RESULTS / "summary.csv", index=False)
summary
