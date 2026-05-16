#!/usr/bin/env python3

"""Generates error ellipses from atcfunix files of an ensemble forecast.

This is a temporary location for this script; the plot_ellipses()
function should be lifted out and put somewhere more sensible.

Command-line arguments:
1. Basin (AL, EP, IO, etc.)
2. Numeric storm id (3, 10, 91, etc.)
3. Analysis time in YYYYMMDDHH format (20251028)
4. Model identifier (GFSO, HFSA, etc.)
5. List of atcfunix filenames

Model identifiers with AVN in atcfunix files are renamed to GFS (ie. AVNO becomes GFSO).

`./ellipses.py AL 13 20251028 HFSA H*/*2025102800*atcfunix`
"""

import sys
import collections
import numpy
import datetime
import math

import cartopy

import matplotlib
from matplotlib import pyplot as plt
from cartopy import crs as ccrs

class AtcfUnixLine:
    """
    Utility class with track information.
    """
    def __init__(self, line):
        # Line looks like this:
        # AL, 10, 2025100712, 03, HFSA, 000, 110N,  430W
        # 0000000000111111111122222222223333333333444444
        # 0123456789012345678901234567890123456789012345

        self.basin2 = line[0:2]
        self.stormid = int(line[4:6].strip(), 10)
        self.YYYYMMDDHH = line[8:18]
        self.atime = datetime.datetime.strptime(self.YYYYMMDDHH, '%Y%m%d%H')
        self.model = line[24:28].strip().replace('AVN', 'GFS')
        self.lead_time_hour = int(line[30:33].strip(), 10)

        lat_int = int(line[35:38].strip(), 10)
        latNS = line[38]
        self.lat = lat_int / 10.0
        if latNS == 'S':
            self.lat = -self.lat

        lon_int = int(line[41:45].strip(), 10)
        lonEW = line[45]
        self.lon = lon_int / 10.0
        if lonEW == 'W':
            self.lon = -self.lon

    def set_ensemble_id(self, ensid):
        self.ensemble_id = ensid

def read_atcfunix(filename, filter_basin2, filter_stormid, filter_atime, filter_model):
    """
    Reads one atcfunix file, scanning for lines that match the filters.

    @returns a list of AtcfUnixLine objects sorted by lead time.
    """
    #print(f'Scan {filename} for basin {filter_basin2} stormid {filter_stormid} atime {filter_atime} model {filter_model}')
    by_time = []
    with open(filename, 'rt') as fd:
        for line in fd:
            parsed = AtcfUnixLine(line)

            if filter_basin2 is not None and filter_basin2 != parsed.basin2:
                #print(f'bad basin {parsed.basin2}: {line}')
                continue
            if filter_stormid is not None and filter_stormid != parsed.stormid:
                #print(f'bad stormid {parsed.stormid}: {line}')
                continue
            if filter_atime is not None and filter_atime != parsed.atime:
                #print(f'bad atime: {line}')
                continue
            if filter_model is not None and filter_model != parsed.model:
                #print(f'bad model: {model}')
                continue

            #print(f'accept line {line}')
            by_time.append(parsed)

    by_time.sort(key=lambda x: x.lead_time_hour)
    return by_time

def recentered_longitudes(inlon):
    """Ensures no break in longitudes when the ensemble crosses a dateline.
    Longitudes are shifted to min(inlon) ... 360+min(inlon)"""
    minlon = min(inlon)
    outlon = [ minlon + (l - minlon) % 360 for l in inlon ]
    return outlon

def read_ensemble(filenames, filter_basin2, filter_stormid, filter_atime, filter_model):
    """
    Reads a list of atcfunix files, one per ensemble member.

    @returns A list, sorted by ensemble id, of lists of AtcfUnixLine objects. The inner lists are the result of a call to read_atcfunix() on one file.
    """
    by_id = [ read_atcfunix(filename, filter_basin2, filter_stormid, filter_atime, filter_model)
              for filename in filenames]
    ensemble_id = -1
    for lines in by_id:
        ensemble_id += 1
        for line in lines:
            line.set_ensemble_id(ensemble_id)
    return by_id

def fixes_by_lead_time(by_id):
    """
    Obtains fixes for each lead time and ensemble member.

    @param by_id the return value of read_ensemble()

    @returns A three-dimensional array fixes[lead_time][ensemble_id][2]. Outer dimension is the lead time, sorted by increasing lead time. Middle dimension is the ensemble id, sorted numerically increasing. Inner dimension is the fix location as [ lon, lat ]
    """

    fixes = collections.defaultdict(dict)
    for by_lead_time in by_id:
        for line in by_lead_time:
            fixes[line.lead_time_hour][line.ensemble_id] = [ line.lon, line.lat ]
    return fixes

def covariance_and_mean_by_lead_time(fixes):
    """
    Calculates covariance matrixes and mean locations for each lead time.

    @param fixes from fixes_by_lead_time()

    @returns A list (one per lead time) of lists. Inner lists have five elements: covariance matrix, mean longitude, mean latitude, list of longitude fixes, and list of latitude fixes.
    """
    cov_and_mean = {}
    for lead_time_hour, fixes_by_id in fixes.items():
        lon = []
        lat = []
        for ensemble_id, fix in fixes_by_id.items():
            lon.append(fix[0])
            lat.append(fix[1])
        if not lon and not lat:
            continue # no data at this time

        lon = recentered_longitudes(lon)

        meanlon = sum(lon) / len(lon)
        meanlat = sum(lat) / len(lat)
        if len(lon) < 2:
            # Need at least 2 points for an error estimate
            cov_and_mean.append([ None, meanlon, meanlat ])
            continue
        normlon = [ x - meanlon for x in lon ]
        normlat = [ y - meanlat for y in lat ]
        cov = numpy.cov(numpy.asarray(normlon), numpy.asarray(normlat))
        cov_and_mean[lead_time_hour] = [ cov, meanlon, meanlat, lon, lat ]
    return cov_and_mean

def plot_ellipses(cov_and_mean, plot_hours, colors):
    """
    Plots a track with error ellipses.

    @param cov_and_mean from covariance_and_mean_by_lead_time
    @param plot_hours list of forecast lead times to plot
    @param colors list of colors cycled through for each lead time
    """
    i = -1
    center_x = []
    center_y = []
    fig = plt.figure(figsize=(9,6), dpi=168)
    #plt.gca().set_projection(ccrs.PlateCarree())
    ax = fig.add_subplot(1,1,1, projection=ccrs.PlateCarree())
    legend_contents = []
    for lead_time_hour, cov_meanlon_meanlat_lon_lat in cov_and_mean.items():
        if lead_time_hour not in plot_hours:
            #print(f'skip {lead_time_hour}hr lead time which was not requested')
            continue

        i += 1

        cov, meanlon, meanlat, lon, lat = cov_meanlon_meanlat_lon_lat
        eig = numpy.linalg.eig(cov)
        del cov

        center_x.append(meanlon)
        center_y.append(meanlat)

        val0 = eig.eigenvalues[0]
        val1 = eig.eigenvalues[1]

        vec0 = eig.eigenvectors[0]
        vec1 = eig.eigenvectors[1]

        del eig

        if val0 > val1:
            anglefrom='val0'
            angle = math.atan2(vec0[1], vec0[0]) * 180 / math.pi
        else:
            anglefrom='val1'
            angle = math.atan2(vec1[1], vec1[0]) * 180 / math.pi

        stdev0 = math.sqrt(val0)
        stdev1 = math.sqrt(val1)

        del val0, val1, vec0, vec1

        color = colors[i % len(colors)]

        stdfac = 2 # *(5.995)**0.5

        plt.scatter(lon, lat, 2, color=color, transform=ccrs.PlateCarree()) # , label=f'{lead_time_hour} hrs')
        #print(f'Ellipse at lon={meanlon} lat={meanlat} width={stdev0*2} height={stdev1*2} angle={angle} from {anglefrom} color={color}')
        ellipse = matplotlib.patches.Ellipse([meanlon, meanlat], width=stdev0*stdfac, height=stdev1*stdfac, angle=angle, edgecolor=color, fill=False, transform=ccrs.PlateCarree(), linewidth=1.5)
        ax.add_patch(ellipse) # , label=f'{lead_time_hour} hrs')

        legend_contents.append(matplotlib.patches.Patch(facecolor=color, alpha=0.7, edgecolor=color, label=f'{lead_time_hour} hrs'))


    print(repr(legend_contents))
    gl = ax.gridlines(draw_labels=True, dms=True, x_inline=False, y_inline=False, alpha=0.5)
    gl.top_labels=False
    gl.right_labels = False
    ax.coastlines()
    plt.plot(center_x, center_y, 'kx-', transform=ccrs.PlateCarree())
    plt.legend(handles=legend_contents)
    plt.show()


def main():
    """Main program. Arguments from sys.argv; see module description for details."""
    filter_basin2 = sys.argv[1]
    filter_stormid = int(sys.argv[2], 10)
    filter_atime = datetime.datetime.strptime(sys.argv[3], '%Y%m%d%H')
    filter_model = sys.argv[4]
    filenames = sys.argv[5:]
    by_id = read_ensemble(filenames, filter_basin2, filter_stormid, filter_atime, filter_model)
    fixes = fixes_by_lead_time(by_id)
    cov_and_mean = covariance_and_mean_by_lead_time(fixes)

    # colors = [ color for color in matplotlib.colors.TABLEAU_COLORS.keys() ]
    colors = [ 'tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:cyan', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:brown' ]
    hours = [ 0, 24, 48, 72, 96, 120 ]
    plot_ellipses(cov_and_mean, hours, colors)

if __name__ == '__main__':
    main()
