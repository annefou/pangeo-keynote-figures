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
# # 01 — Data download
#
# Every input is read from its source, nothing is shipped: Copernicus Sentinel-2 and Sentinel-3 from ESA's
# **EOPF Sample Service** (Zarr, opened lazily with `xr.open_datatree`, only the needed window is read), and
# GBIF plant records through **healpix-connector**'s GBIF connector. The windows are stored as CF NetCDF in
# `data/raw/`, with a source registry in `data/raw/sources.json`. No credentials are needed.

# %%
import sys
from pathlib import Path

# shared settings and helpers live in notebooks/lib/ (works from the repo root and from notebooks/)
sys.path.insert(0, str(next(p for p in (Path.cwd() / "lib", Path.cwd() / "notebooks" / "lib") if p.exists())))
import json
from datetime import date

import numpy as np
import xarray as xr
from pyproj import Transformer

from config import (RAW, S2, S3, TDF_ROW_OFFSET, CATALONIA_ROWS, BOX_CX, BOX_CY, BOX_HALF,
                    GBIF_TAXON, GBIF_YEARS)

RAW.mkdir(parents=True, exist_ok=True)
to_lonlat = Transformer.from_crs(32631, 4326, always_xy=True)


def nc_safe(ds):
    """EOPF keeps its own metadata as nested dicts; NetCDF attributes must be flat, so store those as JSON."""
    for v in list(ds.variables.values()) + [ds]:
        v.attrs = {k: (json.dumps(a) if isinstance(a, (dict, list)) else a) for k, a in v.attrs.items()}
    return ds


def reflectance(url, res):
    return xr.open_datatree(url, engine="zarr", chunks={})[f"measurements/reflectance/{res}"].to_dataset()


# %% [markdown]
# ## Sentinel-2, 20 m, Vallès–Montseny–Maresme (slides 1 and 2)
# T31TDG is fully covered; T31TDF is at the swath edge, so it only fills the rows below T31TDG.

# %%
g = reflectance(S2["T31TDG"], "r20m")[["b04", "b03", "b02"]]
f = reflectance(S2["T31TDF"], "r20m")[["b04", "b03", "b02"]]
r0, r1 = CATALONIA_ROWS
top = g.isel(y=slice(r0, None)).compute()
bottom = f.isel(y=slice(g.sizes["y"] - TDF_ROW_OFFSET, r1 - TDF_ROW_OFFSET)).compute()
cat = xr.concat([top, bottom], dim="y")
cat.attrs.update(source="Copernicus Sentinel-2 L2A via ESA EOPF Sample Service (Zarr)", crs="EPSG:32631",
                 products=" ".join(S2.values()), comment="surface reflectance, bands B04/B03/B02 at 20 m")
nc_safe(cat).to_netcdf(RAW / "s2_catalonia_r20m.nc", encoding={v: {"zlib": True, "complevel": 4} for v in cat.data_vars})
print(dict(cat.sizes))

# %% [markdown]
# ## Sentinel-2, 10 m, the Montseny box (slide 9)

# %%
s = reflectance(S2["T31TDG"], "r10m")[["b02", "b03", "b04", "b08"]]
mont = s.sel(x=slice(BOX_CX - BOX_HALF, BOX_CX + BOX_HALF), y=slice(BOX_CY + BOX_HALF, BOX_CY - BOX_HALF)).compute()
mont.attrs.update(source="Copernicus Sentinel-2 L2A via ESA EOPF Sample Service (Zarr)", crs="EPSG:32631",
                  product=S2["T31TDG"])
nc_safe(mont).to_netcdf(RAW / "s2_montseny_r10m.nc", encoding={v: {"zlib": True} for v in mont.data_vars})
print(dict(mont.sizes))

# %% [markdown]
# ## Sentinel-3 OLCI, ~300 m, around the same box (slide 9)
# OLCI comes in sensor geometry with per-pixel latitude/longitude; we keep the rows/columns that fall near the box.

# %%
m = xr.open_datatree(S3, engine="zarr", chunks={})["measurements"].to_dataset()
lat, lon = m.latitude.values, m.longitude.values
near = (lat > 41.6) & (lat < 41.95) & (lon > 2.2) & (lon < 2.6)
rows, cols = np.where(near)
w = m[["oa04_radiance", "oa06_radiance", "oa08_radiance"]].isel(
    rows=slice(rows.min(), rows.max() + 1), columns=slice(cols.min(), cols.max() + 1)).compute()
w = w.drop_vars([c for c in w.coords if c not in ("latitude", "longitude")])
w.attrs.update(source="Copernicus Sentinel-3 OLCI L1 EFR via ESA EOPF Sample Service (Zarr)", product=S3,
               window=f"rows {rows.min()}-{rows.max()}, columns {cols.min()}-{cols.max()}")
nc_safe(w).to_netcdf(RAW / "s3_montseny_olci.nc")
print(dict(w.sizes))

# %% [markdown]
# ## GBIF plant records in the box, through healpix-connector
# GBIF grows every day: a re-run returns more records than the 861 retrieved on 6 October 2026 for the slide.

# %%
from healpix_connector.region import Region
from healpix_connector.connectors import gbif

lo0, la0 = to_lonlat.transform(BOX_CX - BOX_HALF, BOX_CY - BOX_HALF)
lo1, la1 = to_lonlat.transform(BOX_CX + BOX_HALF, BOX_CY + BOX_HALF)
res = gbif.search(Region.from_bbox(lo0, la0, lo1, la1), taxon_key=GBIF_TAXON, filters={"year": GBIF_YEARS},
                  max_records=5100, pad_deg=0.0)
keep = ("gbifID", "species", "year", "decimalLongitude", "decimalLatitude", "coordinateUncertaintyInMeters")
(RAW / "gbif_montseny.json").write_text(json.dumps(
    {"provenance": res.provenance, "records": [{k: r.get(k) for k in keep} for r in res.records]}, indent=1, default=str))
print(len(res.records), "records")

# %%
sources = [
    {"name": "Copernicus Sentinel-2 L2A (EOPF Zarr sample)", "url": u, "license": "Copernicus open and free data licence",
     "accessed_on": str(date.today())} for u in S2.values()] + [
    {"name": "Copernicus Sentinel-3 OLCI L1 EFR (EOPF Zarr sample)", "url": S3,
     "license": "Copernicus open and free data licence", "accessed_on": str(date.today())},
    {"name": "GBIF occurrence search API (via healpix-connector)", "url": "https://api.gbif.org/v1/occurrence/search",
     "license": "per-record (CC0 / CC BY / CC BY-NC)", "accessed_on": str(date.today()),
     "query": res.provenance["params"]}]
(RAW / "sources.json").write_text(json.dumps(sources, indent=1))
