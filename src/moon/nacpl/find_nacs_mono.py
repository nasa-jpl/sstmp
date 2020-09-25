from nacpl import find_stereo_pairs, geom_helpers
from shapely import wkt
import clize, json, shapely

@clize.parser.value_converter
def list_param(arg):
    return arg.split(',')

def filter_nacs_mono(img_set, min_incidence=30, max_incidence=65):
    """
    Culls NAC images before mono mosaic processing. This initial version only filters by solar incidence angle.
    :param img_set: A GeoDataFrame of NAC imagery
    :return: A GeoDataFrame of NAC imagery containing only suitable mosaic candidates
    """
    
    filtered_img_set = img_set.loc[(img_set.incidence_angle > min_incidence) & (img_set.incidence_angle < max_incidence), :]
    return filtered_img_set

def bounding_box_mono(*, west:float, east:float, south:float, north:float, exclude: list_param=[]):
    """
    Like find_stereo_pairs.bounding_box but finds individual NACs rather than stereo pairs. Useful for creating image
    mosaics when not also computing stereo.
    """
    search_poly_shapely = geom_helpers.corners_to_quadrilateral(west, east, south, north, lonC0=True)
    imgs = find_stereo_pairs.ImageSearch(
        polygon=wkt.dumps(search_poly_shapely)
    )
    # imgs.results = imgs.results.filter_sun_geometry()
    imgs.results = imgs.results.drop(exclude)
    from_image_search(imgs)

def from_csv(filepath):
    #filepath to polygon
    imgs = find_stereo_pairs.find_NACs_under_trajectory(csv_file_path=filepath)
    from_image_search(imgs)

def from_polygon(polygon_wkt):
    imgs = find_stereo_pairs.ImageSearch(polygon=polygon_wkt)
    imgs.results = filter_nacs_mono(imgs.results)
    from_image_search(imgs)

def from_image_search(imgs):
    imgs.results = filter_nacs_mono(imgs.results)
    search_poly_shapely = shapely.wkt.loads(imgs.search_poly)
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
    clize.run(bounding_box_mono, alt=from_polygon)