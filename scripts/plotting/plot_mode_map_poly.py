import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import shapely.geometry as sgeom
import netCDF4 as nc
from matplotlib.colors import ListedColormap
import sys

#f = "mode_000000L_19990101_235900V_000000A_obj.nc"
#f = "mode_000000L_19990111_235700V_000000A_obj.nc"
f = sys.argv[1]
ds = nc.Dataset(f)
print(ds)

fcst_raw = ds['fcst_raw']
print(fcst_raw[:,:])

simp_polys = []
for start_idx, npts in tuple(zip(ds['fcst_simp_bdy_start'][:],ds['fcst_simp_bdy_npts'][:])):
  lats = ds['fcst_simp_bdy_lat'][start_idx:start_idx+npts]
  lons = ds['fcst_simp_bdy_lon'][start_idx:start_idx+npts]
  simp_polys.append(sgeom.Polygon((lon,lat) for lon,lat in tuple(zip(lons,lats))))

fcst_hull_polys = []
for start_idx, npts in tuple(zip(ds['fcst_simp_hull_start'][:],ds['fcst_simp_hull_npts'][:])):
  lats = ds['fcst_simp_hull_lat'][start_idx:start_idx+npts]
  lons = ds['fcst_simp_hull_lon'][start_idx:start_idx+npts]
  fcst_hull_polys.append(sgeom.Polygon((lon,lat) for lon,lat in tuple(zip(lons,lats))))

fcst_clus_polys = []
for start_idx, npts in tuple(zip(ds['fcst_clus_hull_start'][:],ds['fcst_clus_hull_npts'][:])):
  lats = ds['fcst_clus_hull_lat'][start_idx:start_idx+npts]
  lons = ds['fcst_clus_hull_lon'][start_idx:start_idx+npts]
  fcst_clus_polys.append(sgeom.Polygon((lon,lat) for lon,lat in tuple(zip(lons,lats))))

mcols = [(255/255,255/255,255/255),(255/255, 0/255, 0/255)]
maskcols = ListedColormap(mcols)

fig = plt.figure(1, figsize=(8,4))
ax = plt.subplot(111,projection=ccrs.LambertConformal(central_longitude=-97.5,central_latitude=38.5))
ax.set_title('AOD (≥0.3 Threshold)\n', loc='center', size=6, pad=-0.5)
ax.set_title("MODE Objects: RRFS", loc='left', size=6, pad=-0.5)
ax.set_title(f"Init: 2023071600 f71", loc='right', size=6, pad=-0.5)
ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.5)
ax.add_feature(cfeature.STATES, linewidth=0.5)
ax.add_feature(cfeature.BORDERS, linewidth=0.5)
ax.set_extent([-68,-86,34,48])
#[ax.add_geometries([p],ccrs.PlateCarree(),facecolor='none',edgecolor='k',linewidth=1.0,linestyle='--') for p in simp_polys]
#[ax.add_geometries([p],ccrs.PlateCarree(),facecolor='none',edgecolor='r',linewidth=1.0,linestyle='--') for p in fcst_hull_polys]
[ax.add_geometries([p],ccrs.PlateCarree(),facecolor='none',edgecolor='b',linewidth=1.0,linestyle='-') for p in fcst_clus_polys]
ax.pcolormesh(ds['lon'][:][:],ds['lat'][:][:],ds['fcst_raw'][:][:],cmap=maskcols,vmin=0.1,transform=ccrs.PlateCarree())
print(ds['fcst_raw'][:][:].max())
crs = ccrs.LambertConformal(central_longitude=-97.5, central_latitude=38.5)
#plt.show()
plt_name = f"mode_EAST.png"
fig.savefig(plt_name, format='png', dpi=360)
