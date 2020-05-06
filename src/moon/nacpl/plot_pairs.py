"""
Plotting routines for stereo pair footprints
"""
from typing import List
import json
from urllib import request
from pandas import DataFrame
from geopandas import GeoDataFrame
from shapely import wkt
from matplotlib import pyplot

def get_geometry_from_ODE(product_id: str):
    geom_resp = request.urlopen(
        url=f'http://oderest.rsl.wustl.edu/live2/?query=product&result=x&output=json&pdsid={product_id}'
    )
    geom_resp = json.loads(geom_resp.read())
    return geom_resp['ODEResults']['Products']['Product']['Footprint_geometry']

def get_footprints(product_ids: List, plot=True, save_path=None):
    """
    Plot footprints of images, given PDS (Planetary Data System) product IDs
    :param product_ids: Product id, for example M106761561LE
    :return: GeoDataFrame containing the plot footprints
    """
    df = DataFrame({'index': product_ids, 'footprint': product_ids})
    df['footprint'] = df['footprint'].apply(get_geometry_from_ODE).apply(wkt.loads)
    gdf = GeoDataFrame(df, geometry='footprint')
    gdf.geometry = gdf.geometry.boundary
    footprint_plot = gdf.plot(
        column='index',
        legend=True,
        legend_kwds={'loc': 'center left', 'bbox_to_anchor': (1, 0.5)}
    )
    pyplot.xlabel('Longitude, degrees E')
    pyplot.ylabel('Latitude, degrees N')
    return gdf

def get_pair_footprints(pair_ids: List, plot=True, save_path=None):
    """
    Plot or save overlapping areas between pairs of NAC images

    :param save_path: Path to output a vector file of the geometries, or None for no output. File based on extension.
    :param plot: Create a figure
    :param pair_ids: Pair ids, a list given like ['M106761561LExxM1101080055RE', 'M1096364254RExxM1142334242LE']
    :return: GeoDataFrame containing the pair footprints
    """
    pairs = [
        pair_id.split('xx')
        for pair_id
        in pair_ids
    ]
    df = DataFrame(pairs, index=pair_ids, columns=['prod_id_0', 'prod_id_1'])
    df = df.applymap(get_geometry_from_ODE).applymap(wkt.loads)
    df['intersection'] = df.apply(
        lambda a: a[0].intersection(a[1]),
        axis='columns')
    gdf = GeoDataFrame(df, geometry='intersection')
    gdf['pair_ids'] = gdf.index.values
    if save_path:
        if save_path.endswith('.json'):
            save_driver = 'GeoJSON'
        gdf.drop(['prod_id_0', 'prod_id_1'], axis='columns').to_file(save_path, driver=save_driver)
    if plot:
        gdf.geometry = gdf.geometry.boundary
        intersection_plot = gdf.plot(
            column='pair_ids',
            legend=True,
            legend_kwds={'loc': 'center left', 'bbox_to_anchor': (1, 0.5)}
        )
        pyplot.xlabel('Longitude, degrees E')
        pyplot.ylabel('Latitude, degrees N')
    return gdf
