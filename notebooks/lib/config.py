"""Shared constants: products, areas of interest and HEALPix depths (one place, so every step agrees)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW, RESULTS, FIGURES = ROOT / "data" / "raw", ROOT / "results", ROOT / "figures"

EOPF = "https://data.eodc.eu/collections/EOPF_ZARR/products/cpm_v270"
# Copernicus Sentinel-2 L2A, 15 Sep 2026, relative orbit 8 (ESA EOPF Sample Service, Zarr)
S2 = {t: f"{EOPF}/S02MSIL2A/2026/09/15/S2A_MSIL2A_20260915T103701_N0512_R008_{t}_20260915T172409.zarr"
      for t in ("T31TDG", "T31TDF")}
# Copernicus Sentinel-3 OLCI L1 EFR, 15 Sep 2026 (non-time-critical)
S3 = (f"{EOPF}/S03OLCEFR/2026/09/15/"
      "S3A_OL_1_EFR____20260915T101708_20260915T102008_20260916T111656_0179_144_065_2160_PS1_O_NT_004.zarr")

# Slides 1-2: Vallès, Montseny and the Maresme coast, on the T31TDG 20 m grid (UTM 31N).
# T31TDF continues it southwards; its first row sits 5001 rows (100 km - 20 m overlap) below T31TDG's.
TDF_ROW_OFFSET = 5001
COVER_ROWS, COVER_COLS = (3075, 5475), (0, 4266)   # 16:9, the largest cloud- and gap-free window
BAND_ROWS, BAND_COLS = (3975, 5675), (0, 4250)     # 2.5:1 band for slide 2
CATALONIA_ROWS = (3075, 5675)                      # union of the two, downloaded once

# Slide 9: a 15 km box over Montseny, UTM 31N centre and half-size (m)
BOX_CX, BOX_CY, BOX_HALF = 450130, 4624430, 7500
DEPTH_GROUND, DEPTH_S2, DEPTH_S3 = 16, 18, 14   # ~100 m, ~25 m, ~400 m

# GBIF: Plantae (Catalogue of Life XR key "P"), records of 2025-2026, read through healpix-connector
GBIF_TAXON, GBIF_YEARS = "P", "2025,2026"
# Slide 9, panel 4: a 5 km zoom (pixel rows/cols of the 10 m box) on the cluster with the most record precisions
ZOOM_ROW, ZOOM_COL, ZOOM_SIZE = 400, 250, 500
