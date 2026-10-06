# Snakefile: the figures of the keynote "Pangeo: Openness for Sovereignty, Innovation, and Sustainable
# Communities" (OpenEarthMonitor, 7 October 2026). One rule per step; each runs a jupytext notebook.
#
#   pixi run snakemake --cores 1        # everything
#   pixi run snakemake --cores 1 -n     # dry run

NB = "notebooks"
RAW = "data/raw"
RES = "results"
FIG = "figures"


def run(nb):
    return f"cd {NB} && jupytext --to notebook --execute {nb} 2>&1 | tee ../{{log}}"


rule all:
    input:
        f"{FIG}/catalonia_cover.jpg",
        f"{FIG}/catalonia_band.jpg",
        f"{FIG}/bridge_strip.jpg",
        f"{RES}/summary.csv",
        f"{FIG}/photo_credits.json",


# 01: Copernicus Sentinel-2 / Sentinel-3 windows from ESA's EOPF Zarr, GBIF records via healpix-connector
rule data_download:
    output:
        f"{RAW}/s2_catalonia_r20m.nc",
        f"{RAW}/s2_montseny_r10m.nc",
        f"{RAW}/s3_montseny_olci.nc",
        f"{RAW}/gbif_montseny.json",
        f"{RAW}/sources.json",
    log:
        f"{RES}/logs/01_data_download.log",
    shell:
        run("01_data_download.py")


# 02: every source onto WGS84 NESTED HEALPix (dggs-convention Zarr)
rule healpix:
    input:
        f"{RAW}/s2_montseny_r10m.nc",
        f"{RAW}/s3_montseny_olci.nc",
        f"{RAW}/gbif_montseny.json",
    output:
        directory(f"{RES}/montseny_healpix.zarr"),
    log:
        f"{RES}/logs/02_data_clean.log",
    shell:
        run("02_data_clean.py")


# 03: the bridge: each GBIF record on the cell matching its uncertainty, Sentinel-2 read on that cell
rule bridge:
    input:
        f"{RAW}/s2_montseny_r10m.nc",
        f"{RAW}/gbif_montseny.json",
        f"{RES}/montseny_healpix.zarr",
    output:
        f"{RES}/records_support.csv",
        f"{RES}/summary.csv",
    log:
        f"{RES}/logs/03_analysis.log",
    shell:
        run("03_analysis.py")


# 04: the images used in the deck
rule figures:
    input:
        f"{RAW}/s2_catalonia_r20m.nc",
        f"{RES}/montseny_healpix.zarr",
        f"{RES}/records_support.csv",
    output:
        f"{FIG}/catalonia_cover.jpg",
        f"{FIG}/catalonia_band.jpg",
        f"{FIG}/bridge_strip.jpg",
    log:
        f"{RES}/logs/04_figures.log",
    shell:
        run("04_figures.py")


# 05: third-party photos (Wikimedia Commons), licence read from the Commons API
rule photos:
    output:
        f"{FIG}/photo_drone.jpg",
        f"{FIG}/photo_edna.jpg",
        f"{FIG}/photo_lidar.jpg",
        f"{FIG}/photo_credits.json",
    log:
        f"{RES}/logs/05_photos.log",
    shell:
        run("05_photos.py")
