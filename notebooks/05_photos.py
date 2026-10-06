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
# # 05 — Third-party photos on slide 9 (drones, eDNA, LiDAR), with their licences
#
# Downloaded from Wikimedia Commons; licence, author and source are read from the Commons API (extmetadata)
# at run time and written to `figures/photo_credits.json`, so the credits cannot drift from the source.
# The thumbnails are crops: for the CC BY-SA images, the crops are shared under the same licence.

# %%
import html
import io
import json
import re

import requests
from PIL import Image, ImageOps

from config import FIGURES

FIGURES.mkdir(parents=True, exist_ok=True)
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "pangeo-keynote-figures/0.1 (https://github.com/annefou/pangeo-keynote-figures)"}
PHOTOS = [  # file on Commons, output, crop box (left, top, right, bottom) in source pixels or None
    ("Orthomosaic_of_Red_Rocks_by_DroneMapper_and_Falcon_UAV.jpg", "photo_drone.jpg", None),
    ("EDNA_Water_Sampling_(36024122736).jpg", "photo_edna.jpg", None),
    ("Lidar_forestry.png", "photo_lidar.jpg", (500, 105, 800, 290)),  # the classified point cloud only
]

# %%
credits = []
for name, out, box in PHOTOS:
    q = requests.get(API, params={"action": "query", "titles": f"File:{name}", "prop": "imageinfo",
                                  "iiprop": "url|extmetadata", "format": "json"}, headers=UA, timeout=60).json()
    info = next(iter(q["query"]["pages"].values()))["imageinfo"][0]
    meta = {k: v.get("value", "") for k, v in info["extmetadata"].items()}
    img = Image.open(io.BytesIO(requests.get(info["url"], headers=UA, timeout=120).content)).convert("RGB")
    if box:
        img = img.crop(box)
    ImageOps.fit(img, (480, 300), Image.LANCZOS).save(FIGURES / out, quality=88)
    credits.append({"output": out, "source": info["descriptionurl"], "artist": html.unescape(re.sub(r"<[^>]+>", "", meta.get("Artist", ""))).strip(),
                    "licence": meta.get("LicenseShortName", ""), "licence_url": meta.get("LicenseUrl", ""),
                    "changes": ("cropped to the point cloud, then " if box else "") + "cropped to 16:10 and resized to 480x300"})
(FIGURES / "photo_credits.json").write_text(json.dumps(credits, indent=1))
credits
