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
# # 06 — Figures reused from the ESA Frontiers of Science talk (slides 8 and 10)
#
# Two figures of the keynote come from [esa-frontiers-figures](https://github.com/annefou/esa-frontiers-figures)
# (doi:10.5281/zenodo.23002390). Rather than copy the images, this step fetches that repository at a pinned commit
# and re-runs its own plotting scripts, then checks that the result is **pixel-identical** to the figure committed
# there, which is the one used in the deck (file bytes may differ through PNG encoding metadata):
#
# * slide 8 — the HEALPix grid on WGS84 at depth 0, 2, 4 (`sphere-vs-ellipsoid/make_healpix_grid.py`,
#   healpix-geo; Natural Earth 110 m land, public domain, shipped upstream);
# * slide 10 — BIOMASS L2A forest height × GBIF records on HEALPix cells, Beni (`beni-biomass-forest-height/plot_fh3.py`,
#   from the per-cell results of the upstream Beni pipeline; the full pipeline needs an ESA MAAP account and is
#   documented upstream).

# %%
import sys
from pathlib import Path

# shared settings and helpers live in notebooks/lib/ (works from the repo root and from notebooks/)
sys.path.insert(0, str(next(p for p in (Path.cwd() / "lib", Path.cwd() / "notebooks" / "lib") if p.exists())))
import hashlib
import io
import json
import shutil
import subprocess
import tarfile

import numpy as np
import requests
from PIL import Image

from config import RAW, RESULTS, FIGURES

REPO, COMMIT = "annefou/esa-frontiers-figures", "5525727b56a957cdaec245636e62119e58379198"
UP = RAW / "esa-frontiers-figures"
FIGS = {  # upstream script, upstream output, name here
    "sphere-vs-ellipsoid/make_healpix_grid.py": ("sphere-vs-ellipsoid/figure/slide7_globes.png", "slide8_healpix_globes.png"),
    "beni-biomass-forest-height/plot_fh3.py": ("beni-biomass-forest-height/figure/beni_biomass_fh_gbif_zoom.png",
                                               "slide10_beni_biomass_gbif.png"),
}

# %%
shutil.rmtree(UP, ignore_errors=True)   # always start from the commit, so "committed" really is upstream
if True:
    r = requests.get(f"https://codeload.github.com/{REPO}/tar.gz/{COMMIT}", timeout=300)
    r.raise_for_status()
    with tarfile.open(fileobj=io.BytesIO(r.content)) as tar:
        tar.extractall(RAW, filter="data")
    (RAW / f"esa-frontiers-figures-{COMMIT}").rename(UP)

md5 = lambda p: hashlib.md5(Path(p).read_bytes()).hexdigest()
check = {"repository": f"https://github.com/{REPO}", "commit": COMMIT, "figures": []}
FIGURES.mkdir(parents=True, exist_ok=True)
for script, (out, name) in FIGS.items():
    committed = md5(UP / out)                      # the figure as committed upstream (= the deck image)
    before = np.asarray(Image.open(UP / out).convert("RGBA"))
    subprocess.run([sys.executable, str(UP / script)], check=True, cwd=UP / Path(script).parent)
    rerun = md5(UP / out)
    after = np.asarray(Image.open(UP / out).convert("RGBA"))
    shutil.copyfile(UP / out, FIGURES / name)
    check["figures"].append({"script": script, "output": name, "md5_committed": committed, "md5_rerun": rerun,
                             "byte_identical": committed == rerun,
                             "pixel_identical": before.shape == after.shape and bool((before == after).all())})
(RESULTS / "upstream_check.json").write_text(json.dumps(check, indent=1))
check
