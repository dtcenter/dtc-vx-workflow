import argparse
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import glob
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import shapely.geometry as sgeom
import netCDF4 as nc
from matplotlib.colors import ListedColormap

def plot_mode_map_poly(files, debug):

    for f in glob.glob(files):

        print(f"Plotting data for file {f}")
        ds = nc.Dataset(f)

        if debug:
            print(f"{ds=}")
            print(f"{ds.ncattrs()=}")
            print(f"{ds.dimensions.values()=}")
            print(f"{ds.variables.values()=}")

        fcst_raw = ds['fcst_raw']
        obs_raw = ds['obs_raw']
        init_time = fcst_raw.init_time
        valid_time = fcst_raw.valid_time
        if debug:
            print(f"{obs_raw[:,:]=}")
        obtype=getattr(ds, "obtype", "unknown_obtype")
#        simp_polys = []
#        for start_idx, npts in tuple(zip(ds['fcst_simp_bdy_start'][:],ds['fcst_simp_bdy_npts'][:])):
#          lats = ds['fcst_simp_bdy_lat'][start_idx:start_idx+npts]
#          lons = ds['fcst_simp_bdy_lon'][start_idx:start_idx+npts]
#          simp_polys.append(sgeom.Polygon((lon,lat) for lon,lat in tuple(zip(lons,lats))))
#        
#        fcst_hull_polys = []
#        for start_idx, npts in tuple(zip(ds['fcst_simp_hull_start'][:],ds['fcst_simp_hull_npts'][:])):
#          lats = ds['fcst_simp_hull_lat'][start_idx:start_idx+npts]
#          lons = ds['fcst_simp_hull_lon'][start_idx:start_idx+npts]
#          fcst_hull_polys.append(sgeom.Polygon((lon,lat) for lon,lat in tuple(zip(lons,lats))))
        
        minlon=maxlon=minlat=maxlat=0
        fcst_clus_polys = []
        if 'fcst_clus_hull_start' in ds.variables:
            for start_idx, npts in tuple(zip(ds['fcst_clus_hull_start'][:],ds['fcst_clus_hull_npts'][:])):
                lats = ds['fcst_clus_hull_lat'][start_idx:start_idx+npts]
                lons = ds['fcst_clus_hull_lon'][start_idx:start_idx+npts]
                fcst_clus_polys.append(sgeom.Polygon((lon,lat) for lon,lat in tuple(zip(lons,lats))))
                maxlat=max(lats)
                minlat=min(lats)
                maxlon=max(lons)
                minlon=min(lons)

        obs_clus_polys = []
        if 'obs_clus_hull_start' in ds.variables:
            for start_idx, npts in tuple(zip(ds['obs_clus_hull_start'][:],ds['obs_clus_hull_npts'][:])):
                lats = ds['obs_clus_hull_lat'][start_idx:start_idx+npts]
                lons = ds['obs_clus_hull_lon'][start_idx:start_idx+npts]
                obs_clus_polys.append(sgeom.Polygon((lon,lat) for lon,lat in tuple(zip(lons,lats))))
                maxlat=max(lats)
                minlat=min(lats)
                maxlon=max(lons)
                minlon=min(lons)
        if not fcst_clus_polys and not obs_clus_polys:
            print(f"WARNING: no observation or forecast objects found in file: {f}")
            continue
        fig = plt.figure(1, figsize=(8,4))
        ax = plt.subplot(111,projection=ccrs.LambertConformal(central_longitude=-97.5,central_latitude=38.5))
        ax.set_title('AOD (≥0.3 Threshold)\n', loc='center', size=6, pad=-0.5)
#        ax.set_title("MODE Objects: RRFS", loc='left', size=6, pad=-0.5)
        ax.set_title(f"Init: {init_time} Valid: {valid_time}", loc='right', size=6, pad=-0.5)
        ax.add_feature(cfeature.COASTLINE.with_scale('50m'), linewidth=0.5)
        ax.add_feature(cfeature.STATES, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.5)

        bfr=2
        extent=[minlon-bfr,maxlon+bfr,minlat-bfr,maxlat+bfr]
        ax.set_extent(extent)
#        print("Adding simple polygons")
#        for p in simp_polys:
#            ax.add_geometries(
#                [p],
#                crs=ccrs.PlateCarree(),
#                facecolor='none',
#                edgecolor='k',
#                linewidth=1.0,
#                linestyle='--'
#            )
#        print("Adding forecast hull polygons")
#        for p in fcst_hull_polys:
#            ax.add_geometries(
#                [p],
#                crs=ccrs.PlateCarree(),
#                facecolor='none',
#                edgecolor='r',
#                linewidth=1.0,
#                linestyle='--'
#            )
        print("Adding forecast cluster polygons")
        for p in fcst_clus_polys:
            ax.add_geometries(
                [p],
                crs=ccrs.PlateCarree(),
                facecolor='none',
                edgecolor='r',
                linewidth=1.0,
                linestyle='--'
            )
        print("Adding obs cluster polygons")
        for p in obs_clus_polys:
            ax.add_geometries(
                [p],
                crs=ccrs.PlateCarree(),
                facecolor='none',
                edgecolor='g',
                linewidth=1.0,
                linestyle='--'
            )
        fcstcols = ListedColormap([
                       (1.0, 1.0, 1.0, 0.0),  # 0 → fully transparent
                       (0.8, 0.1, 0.1, 0.8),  # 1 → red, translucent
                   ])
        obscols = ListedColormap([
                       (1.0, 1.0, 1.0, 0.0),  # 0 → fully transparent
                       (0.1, 0.8, 0.1, 0.8),  # 1 → green, translucent
                   ])

        ax.pcolormesh(ds['lon'][:][:],ds['lat'][:][:],ds['fcst_raw'][:][:],cmap=fcstcols,vmin=0.1,transform=ccrs.PlateCarree())
        ax.pcolormesh(ds['lon'][:][:],ds['lat'][:][:],ds['obs_raw'][:][:],cmap=obscols,vmin=0.1,transform=ccrs.PlateCarree())
        if debug:
            print(f"{ds['fcst_raw'][:][:].max()=}")
            print(f"{ds['obs_raw'][:][:].max()=}")
        crs = ccrs.LambertConformal(central_longitude=-97.5, central_latitude=38.5)
        #plt.show()
        plt_name=f"mode_{obtype}_fcst_valid_{valid_time}.png"
        print(f"Saving plot {plt_name}")
        fig.savefig(plt_name, format='png', dpi=300)
        plt.close(fig)

if __name__ == "__main__":

    ap = argparse.ArgumentParser(description="Plot MODE objects from netCDF obj files")
    ap.add_argument("-f","--files", required=True, help="Input netCDF file(s)")
    ap.add_argument("-d","--debug", action='store_true', help="Print debug output")
    args = ap.parse_args()

    plot_mode_map_poly(args.files,args.debug)
