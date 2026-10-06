"""Small helpers shared by steps 02-04: pixels to WGS84 NESTED HEALPix cells, per-cell means, dggs Zarr groups."""
import numpy as np
import xarray as xr
from healpix_geo import nested
from healpix_connector.dggs_zarr import dggs_attrs, cf_grid_mapping_attrs
from pyproj import Transformer

ELLIPSOID = "WGS84"
_to_lonlat = Transformer.from_crs(32631, 4326, always_xy=True)


def utm_lonlat(x, y):
    """Lon/lat of every pixel centre of a UTM 31N grid."""
    X, Y = np.meshgrid(x, y)
    return _to_lonlat.transform(X, Y)


def cell_ids(lon, lat, depth):
    return nested.lonlat_to_healpix(np.ravel(lon), np.ravel(lat), np.uint8(depth),
                                    ellipsoid=ELLIPSOID).reshape(np.shape(lon))


def cell_means(values, ids):
    """Mean of each value column over the pixels of each cell. values: (..., k); ids: (...)."""
    u, inv = np.unique(np.ravel(ids), return_inverse=True)
    v = np.asarray(values).reshape(inv.size, -1)
    n = np.bincount(inv)
    return u, np.stack([np.bincount(inv, weights=v[:, k]) / n for k in range(v.shape[1])], -1), n


def lookup(u, table, ids, fill=np.nan):
    """Values of cells ``ids`` from a (cells, k) table indexed by sorted cell ids ``u``."""
    flat = np.ravel(ids)
    j = np.clip(np.searchsorted(u, flat), 0, len(u) - 1)
    hit = u[j] == flat
    out = np.full((flat.size, table.shape[1]), fill, dtype="float64")
    out[hit] = table[j[hit]]
    return out.reshape(np.shape(ids) + (table.shape[1],))


def dggs_dataset(depth, cells, data_vars, **attrs):
    """A dggs-convention dataset (zarr-conventions/dggs v1, as healpix-convert writes it), CF HEALPix grid mapping."""
    ds = xr.Dataset({k: (("cells",), np.asarray(v)) for k, v in data_vars.items()},
                    coords={"cell_ids": (("cells",), np.asarray(cells, dtype="uint64"),
                                         {"standard_name": "healpix_index"})})
    ds["crs"] = xr.DataArray(0, attrs=cf_grid_mapping_attrs(depth))
    for k in data_vars:
        ds[k].attrs["grid_mapping"] = "crs"
    ds.attrs.update(dggs_attrs(depth))
    ds.attrs.update(attrs)
    return ds
