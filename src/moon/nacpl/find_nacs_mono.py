from nacpl import find_stereo_pairs, geom_helpers
from shapely import wkt
import clize, json, shapely

@clize.parser.value_converter
def list_param(arg):
    return arg.split(',')

def bounding_box_mono(*, west:float, east:float, south:float, north:float, exclude: list_param=[]):
    """
    Like find_stereo_pairs.bounding_box but finds individual NACs rather than stereo pairs. Useful for creating image
    mosaics when not also computing stereo.
    """
    search_poly_shapely = geom_helpers.corners_to_quadrilateral(west, east, south, north)
    imgs = find_stereo_pairs.ImageSearch(
        polygon=wkt.dumps(search_poly_shapely)
    )
    imgs.results = imgs.results.drop(exclude)
    imgs.results['geometry'] = imgs.results.footprint_geometry
    # Shrink all the footprints so that there will be overlap in final steps of mosaic creation
    imgs.results['geometry'] = imgs.results.apply(lambda row: shapely.affinity.scale(row.geometry, 0.9, 0.9, 0.9), axis=1)
    imgs, stats = geom_helpers.covering_set_search(
        full_poly_set=imgs.results,
        search_poly=search_poly_shapely,
        verbose=False,
        plot=True
    )
    print(json.dumps(tuple(imgs.index.values)))

if __name__ == '__main__':
    clize.run(bounding_box_mono)