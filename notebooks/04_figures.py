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
# # 04 — Figures used in the keynote
#
# * `figures/catalonia_cover.jpg` — slide 1 (cover), Sentinel-2 true colour, 16:9.
# * `figures/catalonia_band.jpg` — slide 2, the same scene as a 2.5:1 band.
# * `figures/bridge_strip.jpg` (+ the four panels) — slide 9, "From the ground to space"; panel 4 puts each
#   GBIF record on the cell that matches its uncertainty and shows Sentinel-2 averaged on that cell.
#
# Rendering: reflectance scaled by 0.22 (0.20 for the Montseny panels), clipped to [0, 1], gamma 1/1.5.

# %%
import json

import numpy as np
import xarray as xr
from PIL import Image
from scipy import ndimage

from config import (RAW, RESULTS, FIGURES, COVER_ROWS, COVER_COLS, BAND_ROWS, BAND_COLS, CATALONIA_ROWS,
                    DEPTH_GROUND, DEPTH_S2, DEPTH_S3, ZOOM_ROW, ZOOM_COL, ZOOM_SIZE)
from healpix_tools import utm_lonlat, cell_ids, cell_means, lookup

FIGURES.mkdir(parents=True, exist_ok=True)
STORE = RESULTS / "montseny_healpix.zarr"


RECORD = [0, 229, 255]    # cyan: records and precise cells (distinct from vegetation in hue and brightness)
WIDE = [255, 255, 255]    # white: cells of ~800 m and more
HALO = [0, 0, 0]          # black halo around every mark, readable on green and on grey, and in grey-scale


def paint(img, mask, colour, halo=3):
    """Paint ``mask`` in ``colour`` with a black halo of ``halo`` pixels around it."""
    img[ndimage.binary_dilation(mask, iterations=halo) & ~mask] = HALO
    img[mask] = colour


def to_uint8(a, scale):
    return (np.clip(a / scale, 0, 1) ** (1 / 1.5) * 255).astype("uint8")


# %% [markdown]
# ## Slides 1 and 2: the Vallès, Montseny and the Maresme coast

# %%
cat = xr.open_dataset(RAW / "s2_catalonia_r20m.nc")
M = np.stack([cat.b04.values, cat.b03.values, cat.b02.values], -1).astype("float32")
off = CATALONIA_ROWS[0]
cover = M[COVER_ROWS[0] - off:COVER_ROWS[1] - off, COVER_COLS[0]:COVER_COLS[1]]
Image.fromarray(to_uint8(cover, 0.22)).resize((1920, 1080), Image.LANCZOS).save(
    FIGURES / "catalonia_cover.jpg", quality=88)
band = M[BAND_ROWS[0] - off:BAND_ROWS[1] - off, BAND_COLS[0]:BAND_COLS[1]]
Image.fromarray(to_uint8(np.nan_to_num(band, nan=0.22), 0.22)).resize((1980, 792), Image.LANCZOS).save(
    FIGURES / "catalonia_band.jpg", quality=88)

# %% [markdown]
# ## Slide 9: four views of the same 15 km box, all on HEALPix cells
# Every display pixel is a Sentinel-2 10 m pixel; it is coloured by the value of the cell that contains it.

# %%
s2 = xr.open_dataset(RAW / "s2_montseny_r10m.nc")
lon, lat = utm_lonlat(s2.x.values, s2.y.values)
rgb = np.stack([s2.b04.values, s2.b03.values, s2.b02.values], -1).astype("float32")
C = {d: cell_ids(lon, lat, d) for d in {DEPTH_GROUND, DEPTH_S2, DEPTH_S3}}

z18 = xr.open_zarr(STORE, group=f"sentinel2/{DEPTH_S2}")
s2c = lookup(z18.cell_ids.values, np.stack([z18.b04.values, z18.b03.values, z18.b02.values], -1), C[DEPTH_S2])
p2 = to_uint8(s2c, 0.20)
p2_framed = p2.copy()
r0, c0, n = ZOOM_ROW, ZOOM_COL, ZOOM_SIZE
for sl in [(slice(r0, r0 + 6), slice(c0, c0 + n)), (slice(r0 + n - 6, r0 + n), slice(c0, c0 + n)),
           (slice(r0, r0 + n), slice(c0, c0 + 6)), (slice(r0, r0 + n), slice(c0 + n - 6, c0 + n))]:
    p2_framed[sl] = 255
for sl in [(slice(r0 - 3, r0), slice(c0 - 3, c0 + n + 3)), (slice(r0 + n, r0 + n + 3), slice(c0 - 3, c0 + n + 3)),
           (slice(r0 - 3, r0 + n + 3), slice(c0 - 3, c0)), (slice(r0 - 3, r0 + n + 3), slice(c0 + n, c0 + n + 3))]:
    p2_framed[sl] = 0
Image.fromarray(p2_framed).save(FIGURES / "panel2_sentinel2_d18.png")

z3 = xr.open_zarr(STORE, group=f"sentinel3/{DEPTH_S3}")
p3 = lookup(z3.cell_ids.values, np.stack([z3.oa08_radiance.values, z3.oa06_radiance.values,
                                          z3.oa04_radiance.values], -1), C[DEPTH_S3])
# display only: scale each OLCI radiance band to the Sentinel-2 reflectance of the same cells (median ratio),
# so that the panels differ by resolution, not by colour
_, s2at14, _ = cell_means(rgb, C[DEPTH_S3])
s2at14 = lookup(np.unique(C[DEPTH_S3]), s2at14, C[DEPTH_S3])
for k in range(3):
    p3[..., k] *= np.nanmedian(s2at14[..., k]) / np.nanmedian(p3[..., k])
Image.fromarray(to_uint8(np.nan_to_num(p3, nan=1), 0.20)).save(FIGURES / "panel3_sentinel3_d14.png")

g16 = xr.open_zarr(STORE, group=f"gbif/{DEPTH_GROUND}")
grey = p2.astype("float32").mean(-1, keepdims=True)
p1 = (0.35 * grey + 0.65 * 255) * np.ones((1, 1, 3))
paint(p1, ndimage.binary_dilation(np.isin(C[DEPTH_GROUND], g16.cell_ids.values), iterations=1), RECORD, halo=2)
Image.fromarray(p1.astype("uint8")).save(FIGURES / "panel1_gbif_d16.png")

# panel 4: a 5 km zoom. Each record sits on the cell matching its uncertainty, drawn over Sentinel-2 at 10 m:
# filled cyan for cells of ~25-50 m (depth 17-18), cyan outlines for ~100-400 m, white for ~800 m-6 km;
# all with a black halo (distinct from vegetation also for red-green colour blindness). Cells larger than ~6 km (depth < 10)
# do not fit in the box and are only counted (results/summary.csv).
import pandas as pd
rec = pd.read_csv(RESULTS / "records_support.csv")
rec = rec[rec.depth >= 10]
zr, zc = slice(ZOOM_ROW, ZOOM_ROW + ZOOM_SIZE), slice(ZOOM_COL, ZOOM_COL + ZOOM_SIZE)
zlon, zlat = lon[zr, zc], lat[zr, zc]
up = 3                                                   # draw at 3x so outlines stay crisp
zlon = np.kron(zlon, np.ones((up, up))); zlat = np.kron(zlat, np.ones((up, up)))
base = np.kron(to_uint8(rgb[zr, zc], 0.20), np.ones((up, up, 1)))
p4 = 0.85 * base.astype("float32") + 0.15 * 255
mark = np.zeros(p4.shape[:2], bool)
wide = np.zeros(p4.shape[:2], bool)                     # cells of ~800 m and more: white
for d, grp in rec.groupby("depth"):
    Cd = cell_ids(zlon, zlat, d)
    inside = np.isin(Cd, np.unique(grp.cell_id.values.astype("uint64")))
    if not inside.any():
        continue
    if d >= 17:
        mark |= ndimage.binary_dilation(inside, iterations=7)
    else:
        border = np.zeros_like(inside)
        for ax in (0, 1):
            diff = np.diff(Cd, axis=ax) != 0
            sl = [slice(None)] * 2; sl[ax] = slice(1, None); border[tuple(sl)] |= diff
            sl[ax] = slice(None, -1); border[tuple(sl)] |= diff
        ring = inside & ndimage.binary_dilation(border, iterations=6)
        if d <= 13:
            wide |= ring
        else:
            mark |= ring
paint(p4, wide, WIDE, halo=3)
paint(p4, mark, RECORD, halo=3)
Image.fromarray(p4.astype("uint8")).save(FIGURES / "panel4_bridge_support.png")

# %%
S, gap = 760, 24
strip = Image.new("RGB", (4 * S + 3 * gap, S), "white")
for i, name in enumerate(["panel1_gbif_d16", "panel2_sentinel2_d18", "panel3_sentinel3_d14", "panel4_bridge_support"]):
    strip.paste(Image.open(FIGURES / f"{name}.png").resize((S, S), Image.LANCZOS), (i * (S + gap), 0))
strip.save(FIGURES / "bridge_strip.jpg", quality=90)
strip
