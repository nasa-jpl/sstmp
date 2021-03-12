import numpy as np
import shapely
from shapely.geometry import MultiPoint, Polygon, Point
from shapely.ops import cascaded_union
from matplotlib import pyplot
import geopandas
from typing import Optional

def corners_to_quadrilateral(west, east, south, north, lonC0=False):
    """
     
    :param lonC0: Boolean. If true, expects -180 to +180 longitudes (centered on 0) and converts them to 0 to 360 
    :return: 
    """
    
    west, east, south, north = [float(cardinal_dir) for cardinal_dir in (west, east, south, north)]
    try:
        assert -180 < west < east < 180
    except AssertionError:
        print("Problem with longitude values. Please ensure west is less than east, and you are using -180 to 180 longitude.")
    
    try:
        assert -90 < south < north < 90
    except AssertionError:
        print("Problem with latitude values. Please ensure south is less than north, and you are using -90 to 90 latitude.")

    # We always work in 0 to 360 lon because we use the ODE REST api, which likes that.
    if lonC0:
        east, west = [lon + 360 for lon in (east, west) if lon < 0]

    return Polygon((
        (west, north), (east, north), (east, south), (west, south)
    ))

def draw_ellipse(center: [float, float],
                 semimajor: float, semiminor: float,
                 rotation: float, save_to: Optional[str] = None):
    circle = Point(center).buffer(1)
    ellipse = shapely.affinity.scale(circle, semimajor, semiminor)
    ellipse_rotated = shapely.affinity.rotate(ellipse, rotation)
    gdf = geopandas.GeoDataFrame()
    gdf.geometry = [ellipse_rotated]
    gdf.plot()
    return gdf

def check_if_polys_cover_bb(polys, bb, buffer=0.01):
    """
    Check if the set of polygons polys fully covers the bounding box bb.
    :param polys: A geopandas geoseries of polygons
    :param bb: A bounding polygon as a shapely Polygon
    :return: boolean indicating whether the bounding box is fully covered
    """

    polys_union = cascaded_union(polys.buffer(buffer).geometry)
    return polys_union.contains(bb)


def covering_set_search(full_poly_set, search_poly, success_fraction=0.99,
                        miss_limit=10, rank_by=None, plot=False, verbose=True):
    """
    Finds a set of polygons taken from full_poly_set which fully cover as much of search_poly as possible.

    Replaces find_stereo_pairs.StereoPairSet.find_covering_set and find_polys_from_points

    :param full_poly_set: geopandas.GeoDataFrame whose geometry is a series of shapely polygons
    :param search_poly: shapely.Polygon A polygon to search within
    :param rank_by: str Column of the full_poly_set to use to prioritse the polygons for inclusion
    :param success_fraction: float Fraction of coverage at which to stop searching
    :param miss_limit: int Number of checked locations
    :param plot: bool Whether to draw a progress figure each step using matplotlib
    :return: (GeoDataFrame, stats) GeoDataFrame has rows selected from full_poly_set, maintaining all columns. stats
    contains coverage percent achieved and miss count.
    """

    coverage_fraction = 0.0
    miss_count = 0
    selected_polys = geopandas.GeoDataFrame()
    remaining_uncovered_poly = search_poly #TODO sort by rank_by
    selected_poly = None
    search_points = geopandas.GeoDataFrame(columns=['hit', 'geometry'])
    search_poly_gdf = geopandas.GeoDataFrame({'geometry': [search_poly.boundary]})
    while coverage_fraction < success_fraction and miss_count < miss_limit:
        # Select a point at a inside search_poly
        search_point = remaining_uncovered_poly.representative_point()

        # Maybe move the point a bit

        # Find the first polygon in full_poly_set containing this point and add it to selected_polys
        hit = False
        for ind, poly_row in full_poly_set.iterrows():
            if poly_row.geometry.contains(search_point):
                hit = True
                selected_poly = poly_row.geometry
                selected_polys = selected_polys.append(poly_row)
                # Subtract the selected polygon from the remaining_uncovered_poly
                remaining_uncovered_poly = remaining_uncovered_poly.difference(selected_poly)
                # Calculate the coverage fraction
                coverage_fraction = 1 - (remaining_uncovered_poly.area / search_poly.area)
                if verbose:
                    print(f'Achieved coverage: {coverage_fraction}, success set to {success_fraction}')
                break

        # If we got through all of the polygons and none contained the point, increment miss counter
        if hit == False:
            miss_count += 1
            if verbose:
                print(f'misses: {miss_count} / {miss_limit}')

        # Store the search point in case we want to look at the search pattern
        search_points = search_points.append({'hit': hit, 'search_point': search_point}, ignore_index=True)

        # Maybe plot stuff
        if plot:
            from matplotlib import pyplot
            # Plot the search polygon
            plotax = search_poly_gdf.boundary.plot()

            # Plot the selected polygons
            selected_polys['pair_id'] = selected_polys.index #b/c geopandas doesn't accept index in column arg to plot()
            selected_polys.plot(
                column='pair_id',
                legend=True,
                legend_kwds={'loc': 'center left', 'bbox_to_anchor': (1, 0.5)},
                ax=plotax
            )
            pyplot.savefig(fr'C:\tmp\coversearch\{len(search_points)}')
            pyplot.close('all')
            # Plot the search points
            # TODO

    stats = {'fail_count': miss_count, 'coverage_fraction': coverage_fraction}
    return selected_polys, stats

