"""
Find stereo pair candidates in bounding box
Aaron Curtis
2019-10-15
"""

# TODO check that none of the filters modify self.pairs when inplace is False

# after upgrade to python3:
# TODO add type hinting
# TODO make addition of inplace parameter into a decorator


from nacpl import get_NAC_info_DSBservice, geom_helpers, load_nac_metadata
from shapely.geometry import Polygon, LineString
from shapely import wkt
import geopandas, pandas
import re
import numpy
import urllib
import json

lblfilepath = r'/INDEX.LBL'
indfilepath = r'/CUMINDEX.TAB'

def nac_url_to_id(url):
    """
    Extracts the NAC Product Id from an ASU LROC URL `url`.
    `url` is expected to be in the form:
    http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0001/DATA/COM/2009220/NAC/M104354152LE.IMG'
    where M104354152L is the Product Id

    :return: the Product Id
    """
    prod_id = re.findall('M\d*?[LR]', url)
    assert len(prod_id) == 1
    return prod_id[0]

def to_numeric_or_date(series):
    try:
        return pandas.to_numeric(series, errors='ignore')
    except ValueError:
        return pandas.to_datetime(series, errors='ignore')

def both_in_range(prop, minimum, maximum, dataframe):
    bool_series = (
        (dataframe[prop + '_1'] > minimum) &
        (dataframe[prop + '_1'] < maximum) &
        (dataframe[prop + '_2'] > minimum) &
        (dataframe[prop + '_2'] < maximum)
    )
    return bool_series

def find_NACs_under_trajectory(csv_file_path: str,
                               buffersize=0.5,
                               tolerance=0.05):
    """
    Finds NAC images to cover all points in csv_file

    :param csv_file: Path to a comma separated values file in lat lon format, with header: point, lat, lon
    :param buffersize: Determines the radius of the polygon around the trajectory to search
    :param tolerance: Distance threshold for polygon simplification
    :return: An ImageSearch instance
    """

    # Convert from csv input file to WKT buffer polygon
    df = pandas.read_csv(csv_file_path, dtype=float)
    points = df.loc[:, ['lon', 'lat']].values
    points = LineString(points)
    pointzone = Polygon(points.buffer(buffersize).simplify(tolerance=tolerance).exterior)
    pointzone_wkt = wkt.dumps(pointzone, rounding_precision=3)

    # Instantiate an ImageSearch using that polygon
    return ImageSearch(polygon=pointzone_wkt)

def pair_id(pair):
    try:
        if pair.prod_id_1 < pair.prod_id_2:
            return pair.prod_id_1 + 'xx' + pair.prod_id_2
        else:
            return pair.prod_id_2 + 'xx' + pair.prod_id_1
    except TypeError:
        return None

class ImageSearch:
    """
    Class representing an image search. Results are a GeoDataFrame at imageSearchInstance.results, imageSearchInstance
    is an instance of ImageSearch.

    May be initialized with a WKT string representing a polygon. In that case, it will find all footprints intersecting
    that polygon.

    Otherwise, initialization arguments are same as get_NAC_info_DSBservice.get_NAC_info_bbox_DSBservice. In this case,
    a bounding box can be searched using the arguments east, west, north, south, which represent the edges of the
    bounding box.
    """

    def __init__(self, *args, **kwargs):
        self.search_args = args
        self.search_kwargs = kwargs
        if 'polygon' in kwargs.keys():
            self.search_poly = kwargs['polygon']
            self.results = self._search_from_poly(polygon=kwargs['polygon'])
        else:
            self.results = self._search_from_bb(*args, **kwargs)

    @staticmethod
    def _search_from_poly(polygon: str,
                          indfilepath=indfilepath,  #TODO need better solution than hardcoding path to local files
                          lblfilepath=lblfilepath,
                          verbose=False
                          ):

        pointzone_urlstring = urllib.parse.quote_plus(polygon)
        count_url = f'http://oderest.rsl.wustl.edu/live2/?query=products&target=moon&results=c&ihid=lro&iid=lroc&pt=EDRNAC&output=JSON&limit=1000&footprint={pointzone_urlstring}&loc=f'
        count_resp = urllib.request.urlopen(count_url)
        count_resp = json.loads(count_resp.read())
        count = int(count_resp['ODEResults']['Count'])
        if verbose:
            print(f'Found {count} NAC footprints under the trajectory, will look up their product IDs now')
        # Not necessary to limit the footprint query using the count query, but default limit is 100 so need to set it to
        # something; might as well be the expected number of returned footprints
        req_url = f'http://oderest.rsl.wustl.edu/live2/?query=products&target=moon&results=pm&ihid=lro&iid=lroc&pt=EDRNAC&output=JSON&limit={count}&footprint={pointzone_urlstring}&loc=f'
        resp = urllib.request.urlopen(req_url)
        resp = json.loads(resp.read())
        if verbose:
            print(f'Looking in CUMINDEX.TAB for sun & spacecraft geometry info')
        metadata = load_nac_metadata.load_nac_index(indfilepath=indfilepath, lblfilepath=lblfilepath)
        metadata.product_id = metadata.product_id.apply(str.strip)
        metadata.set_index('product_id', inplace=True)
        footprints = pandas.DataFrame(resp['ODEResults']['Products']['Product'])
        # lowercase all column names for ease of joining from different APIs
        footprints.columns = [col.lower() for col in footprints.columns]
        footprints.set_index('pdsid', inplace=True)
        footprints = footprints.join(metadata, how='inner', lsuffix='_ode', rsuffix='')
        # For the columns that were in common between CUMINDEX.TAB and ODE REST API, remove the ODE ones and keep the ones form CUMINDEX.TAB
        footprints = footprints.loc[:,
                     [col for col in footprints.columns if not col.endswith('_ode')]
                     ]
        footprints = footprints.apply(to_numeric_or_date)
        footprints.footprint_geometry = footprints.footprint_geometry.apply(wkt.loads)
        if verbose:
            print(f'{len(footprints)} NACs were listed in the CUMINDEX.TAB file')
        footprints = geopandas.GeoDataFrame(footprints, geometry='footprint_geometry')
        footprints.crs = '+proj=longlat +a=1737400 +b=1737400 +no_defs'
        footprints.geometry = footprints.footprint_geometry
        # Upcast from shapely LineString to shapely Polygon
        footprints.footprint_geometry = footprints.footprint_geometry.apply(
            lambda footprint: Polygon(footprint)
        )
        footprints.crs = '+proj=longlat +a=1737400 +b=1737400 +no_defs'
        return footprints

    @staticmethod
    def _search_from_bb(*args, **kwargs):
        search_results = get_NAC_info_DSBservice.get_NAC_info_bbox_DSBservice(
            *args, **kwargs, verbose=False
        )
        search_dict = {
            nac_url_to_id(res['url']): res
            for res in search_results
        }
        gdf = geopandas.GeoDataFrame(search_dict).transpose()
        gdf = gdf.apply(to_numeric_or_date)
        gdf.crs = '+proj=longlat +a=1737400 +b=1737400 +no_defs'
        gdf.crs = '+proj=longlat +a=1737400 +b=1737400 +no_defs' #AKA IAU2000:30100, ESRI:104903, GCS_Moon_2000
        gdf = gdf.loc[:,[col for col in gdf.columns if not col.startswith('wac')]]
        #Create shapely polygons from image corners
        corners = (
            'upper_left',
            'upper_right',
            'lower_right',
            'lower_left'
        )
        for prod_id in gdf.index:
            gdf.loc[prod_id, 'polygon'] = Polygon(
                [
                    (gdf.loc[prod_id, corner + '_longitude'],
                     gdf.loc[prod_id, corner + '_latitude'])
                    for corner in corners
                ]
            )
        gdf.set_geometry('polygon', inplace=True)
        return gdf

    def date_range(self):
        return self.results.start_time.min(), self.results.stop_time.max()

    def overlaps(self):
        return StereoPairSet(self)

    def plot_overlaps(self):
        from matplotlib import pyplot
        self.overlaps().plot(facecolor='none', edgecolor='k')
        pyplot.show()

class StereoPairSet:
    """
    Class representing a set of stereo pairs. Instantiate using an ImageSearch instance.

    >>> imgs = ImageSearch(25, 25.8, 45, 45.8) # doctest: +ELLIPSIS
    Found ... images!!

    >>> pairset = StereoPairSet(imgs)
    >>> pairset.pairs.info() # doctest: +ELLIPSIS
    <class 'geopandas.geodataframe.GeoDataFrame'>
    ...

    >>> filtered_pairset = pairset.filter_date_range('2013','2017').filter_sun_geometry().filter_small_overlaps()
    >>> filtered_pairset.pairs.info() # doctest: +ELLIPSIS
    <class 'geopandas.geodataframe.GeoDataFrame'>
    Index: 151 entries, M1126956963RxxM1156415500R to M1142284165LxxM1218779921R
    Columns: 138 entries, center_latitude_1 to area_m2
    dtypes: datetime64[ns](6), float64(99), geometry(1), object(32)
    memory usage: ...

    >>> covering_set = pairset.find_covering_set(25, 25.8, 45, 45.8)
    >>> covering_set.head()
    pair_id
    M1126956963LxxM1134024492R    POLYGON ((25.21000 45.94000, 25.24139 45.37722...
    M1114008179LxxM1123434946R    POLYGON ((25.18392 46.09989, 25.54259 46.09020...
    M1114008179RxxM1123434946L    POLYGON ((25.43000 43.75000, 25.46338 44.59117...
    M1126956963LxxM1134024492R    POLYGON ((25.21000 45.94000, 25.24139 45.37722...
    M1114008179LxxM1123434946R    POLYGON ((25.18392 46.09989, 25.54259 46.09020...
    Name: geometry, dtype: geometry

    """
    def __init__(self, imagesearch=None, pairs=None):
        # If StereoPairSet is instantiated with another StereoPairSet, copy the pairs
        if pairs is not None:
            self.pairs = pairs
        elif imagesearch is not None:
            gdf = imagesearch.results
            gdf['prod_id'] = gdf.index  # Store index (product id) in column so that it's preserved in spatial join operation
            self.pairs = geopandas.overlay(gdf, gdf, how='union')
            pairs_eqc = self.pairs.to_crs(
                "+proj=eqc +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m +no_defs"
            )
            self.pairs['area_m2'] = pairs_eqc.area    # Store area as column before sorting (could use key fn instead...)
            self.pairs.sort_values('area_m2', ascending=False, inplace=True)
            self.filter_unique(inplace=True)  # TODO pair_id is created inside this method call -- maybe not the best place for that
            self.pairs.set_index('pair_id', inplace=True)
            self.bb_covering_pairs = None
        else:
            raise TypeError("Need either imagesearch or pairs argument to instantiate StereoPairSet")

    def filter_new_pairs(self, since, inplace=True):
        """
        Finds stereo pairs that have recently become available due to addition of new data.
        :param since: Any date / time format accepted as a pandas indexer
        :param inplace: Replace .pairs of this StereoPairSet instance with the filtered version
        :return: StereoPairSet of stereo pairs where at least one of the images is newer than since
        """
        filtered_pairs = self.pairs[(self.pairs.start_time_1 > since) | (self.pairs.start_time_2 > since)]
        if inplace:
            self.pairs = filtered_pairs
        return StereoPairSet(pairs=filtered_pairs)

    def filter_date_range(self, startime, endtime, inplace=True):
        """
        Finds stereo pairs where both images were acquired after startime and before endtime.
        :param startime: Any date / time representation accepted by Pandas for slicing
        :param endtime: Any date / time representation accepted by Pandas for slicing
        :param inplace:
        :return: StereoPairSet of stereo pairs where both images were acquired between startime and endtime.
        """
        filtered_pairs = both_in_range('start_time', minimum=startime, maximum=endtime, dataframe=self.pairs)
        if inplace:
            filtered_pairs = self.pairs[filtered_pairs]
        return StereoPairSet(pairs=filtered_pairs)

    def filter_sufficient_convergence(self, min_convergence=2, inplace=True):
        """
        Removes stereo pairs which have an emission angle difference of less than min_convergence degrees.
        :param inplace: Replace .pairs of this StereoPairSet instance with the filtered version
        :param min_convergence: Convergence angle beneath which to remove pair
        :return: StereoPairSet with pairs that have insufficient convergence removed.
        """
        filtered_pairs = self.pairs[numpy.abs(self.pairs.emission_angle_1 - self.pairs.emission_angle_2) > min_convergence]
        if inplace:
            self.pairs = filtered_pairs
        return StereoPairSet(pairs=filtered_pairs)

    def filter_sun_geometry(self, max_sun_azimuth_ground_difference=20, max_incidence_angle_difference=20, inplace=True):
        """
        Removes stereo pairs which have incompatible sun geometry.
        :param max_sun_azimuth_ground_difference: Maximum sun azimuth difference, in degrees.
        :param max_incidence_angle_difference: Maximum sun incidence angle difference, in degrees.
        :param inplace: Replace .pairs of this StereoPairSet instance with the filtered version
        :return: StereoPairSet of pairs with bad sun geometry pairs removed.
        """
        big_incidence_diff = numpy.abs(self.pairs.incidence_angle_1 - self.pairs.incidence_angle_2) < max_incidence_angle_difference
        sub_solar_ground_az_1 = self.pairs.north_azimuth_1 - self.pairs.sub_solar_azimuth_1
        sub_solar_ground_az_2 = self.pairs.north_azimuth_2 - self.pairs.sub_solar_azimuth_2
        sub_solar_ground_az_diff = numpy.abs(sub_solar_ground_az_1 - sub_solar_ground_az_2)
        big_sunaz_diff = sub_solar_ground_az_diff < max_sun_azimuth_ground_difference
        filtered_pairs = self.pairs[big_incidence_diff & big_sunaz_diff]
        if inplace:
            self.pairs = filtered_pairs
        return StereoPairSet(pairs=filtered_pairs)

    def filter_small_overlaps(self, min_area=50000000, inplace=True):
        """
        Removes stereo pairs with insufficient overlap area.
        :param min_area: Minimum overlap area, in square meters.
        :param inplace: Replace .pairs of this StereoPairSet instance with the filtered version
        :return: StereoPairSet with small-overlap pairs removed.
        """
        filtered_pairs = self.pairs[self.pairs.area_m2 > min_area]
        if inplace:
            self.pairs = filtered_pairs
        return StereoPairSet(pairs=filtered_pairs)

    def filter_unique(self, inplace=True):
        """
        Remove self-pairs (e.g. M1234LxxM1234L)
        :param inplace: Replace .pairs of this StereoPairSet instance with the filtered version
        :return: StereoPairSet with self-pairs removed.
        """
        filtered_pairs = self.pairs[self.pairs.loc[:, 'prod_id_1'] != self.pairs.loc[:, 'prod_id_2']]
        # Remove flipped-pair-order pairs (e.g. M1234LxxM4567L where M4567LxxM1234L exists in the same dataset)
        # First, create a column of pair ids, always with the low number first
        filtered_pairs.loc[:, 'pair_id'] = filtered_pairs.apply(pair_id, axis=1)
        filtered_pairs.drop_duplicates(subset='pair_id', inplace=True)
        if inplace:
            self.pairs = filtered_pairs
        return StereoPairSet(pairs=filtered_pairs)

    def filter_incidence(self, inplace=True):
        """
        Remove pair unless both images have 40 < incidence angle < 65
        :param inplace: Replace .pairs of this StereoPairSet instance with the filtered version
        :return: StereoPairSet with bad incidence angle pairs removed.
        """
        filtered_pairs = self.pairs.loc[both_in_range('incidence_angle', 40, 65, self.pairs), :]
        # Remove pair unless both images have emission angle < 45
        filtered_pairs = filtered_pairs.loc[both_in_range('emission_angle', 40, 65, filtered_pairs), :]
        # TODO maybe add phase angle
        if inplace:
            self.pairs = filtered_pairs
        return StereoPairSet(pairs=filtered_pairs)

    def stereo_quality(self):
        """
        Calculates quality metrics for stereo pairs based on:
            Becker et al. 2015. "Criteria for Automated Identification of Stereo Image Pairs."

        :param pair: A geodataframe as returned from find_stereo_pairs.overlaps()
        :return: A dataframe of stereo quality metrics indexed using the prod_id
        """
        pairs = self.pairs
        metrics = pandas.DataFrame(
            columns=['Resolution ratio', 'Parallax/height ratio', 'Shadow tip distance'],
            index=pairs.index
        )

        resolutions = pairs.loc[:, ['resolution_1',
                                    'resolution_2']].to_numpy()  # Converting to numpy for sorting because Pandas can't do this kind of sort
        resolutions.sort()  # numpy does things inplace
        metrics['Resolution ratio'] = resolutions[:, 1] / resolutions[:, 0]

        px1 = - numpy.tan(pairs.emission_angle_1) * numpy.cos(pairs.north_azimuth_1)  # parallax x, image 1
        py1 = numpy.tan(pairs.emission_angle_1) * numpy.sin(pairs.north_azimuth_1)  # parallax y, image 1
        px2 = - numpy.tan(pairs.emission_angle_2) * numpy.cos(pairs.north_azimuth_2)  # parallax x, image 2
        py2 = numpy.tan(pairs.emission_angle_2) * numpy.sin(pairs.north_azimuth_2)  # parallax y, image 2
        metrics['Parallax/height ratio'] = ((px1 - px2) ** 2 + (
                    py1 - py2) ** 2) ** 0.5  # related to convergence angle ("stereo strength")

        shx1 = - numpy.tan(pairs.incidence_angle_1) * numpy.cos(pairs.sub_solar_azimuth_1)
        shy1 = numpy.tan(pairs.incidence_angle_1) * numpy.sin(pairs.sub_solar_azimuth_1)
        shx2 = - numpy.tan(pairs.incidence_angle_2) * numpy.cos(pairs.sub_solar_azimuth_2)
        shy2 = numpy.tan(pairs.incidence_angle_2) * numpy.sin(pairs.sub_solar_azimuth_2)
        metrics['Shadow tip distance'] = ((shx1 - shx2) ** 2 + (
                    shy1 - shy2) ** 2) ** 0.5  # Shadow-tip distance (measure of illumination compatibility)

        limits = {
            'Resolution ratio': (0, 4),  # Paper recommends
            'Parallax/height ratio': (0.1, 1),  # TODO units?
            'Shadow tip distance': (0, 100)  # in deg, TODO check if we need to convert from rad
        }

        normalized_metrics = {
            metric: value / (limits[metric][1] - limits[metric][0])
            for metric, value in metrics.items()
        }

        metrics['Overall quality'] = pandas.DataFrame(normalized_metrics).prod(axis='columns')
        metrics['Area m2'] = pairs.area_m2

        return metrics

    def find_covering_set_poly(self, polygon: str, plot=False):
        """
        Convenience wrapper for using find_covering_set with a search polygon which computes the bounding box for you

        :param polygon: A polygon in which find_covering_set will search
        """
        #Convert from WKT string to shapely
        polygon = wkt.loads(polygon)
        west, south, east, north = polygon.bounds
        self.find_covering_set(west=west,
                               east=east,
                               south=south,
                               north=north,
                               clip_to_polygon=polygon,
                               grid_n_initial=75,
                               grid_n_limit=77,
                               grid_n_step=2,
                               plot=plot)


    def find_covering_set_gridmethod(self, west, east, south, north,
                          grid_n_initial=3,
                          grid_n_limit=20,
                          grid_n_step=2,
                          clip_to_polygon=None,
                          plot=False):
        """
        DEPRECATED: This has been replaced by the generally better geom_helpers.covering_set_search and will be removed
        in a future version.

        Searches for a subset of pair overlaps that completely fill the given bounding box, and sets this StereoPairSet's
        bb_covering_pairs property to a GeoSeries containing those overlaps.

        Expects self.pairs are already sorted by area, from biggest to smallest.

        This is my "naiive solution" to my Stackexchange question here:
            https://math.stackexchange.com/questions/3427888/choose-irregular-polygons-from-a-list-of-irregular-polgyons-to-cover-a-quadrila

        :param grid_n_initial: Number of points on each side to start with for grid search
        :param grid_n_limit: Number of points on each side to increase by each step
        :param grid_n_step: Number of points on each side when to call off the search
        :param plot: Plots footprints for each iteration step if True
        :param clip_to_polygon: A shapely polygon to search inside. Grid points outside of the polygon will be
        discarded.
        :return: If a covering set is found, returns that set as a StereoPairSet. If not, False.
        """
        bb = geom_helpers.corners_to_quadrilateral(west, east, south, north)
        covered = False
        grid_n = grid_n_initial
        while not covered:
            # Generate a grid of points at which to select stereo pairs
            points = geom_helpers.fill_rect_with_points(west, east, south, north, lat_count=grid_n, lon_count=grid_n)
            # If we have a clipping polygon, remove points from our point grid which lie outside the polygon
            if clip_to_polygon:
                points = [point for point in points if point.within(clip_to_polygon)]
            selected_polys_array, selected_polys_geoseries = geom_helpers.find_polys_from_points(
                self.pairs.geometry, points, detailed_output=True)
            if clip_to_polygon:
                covered = geom_helpers.check_if_polys_cover_bb(selected_polys_geoseries, clip_to_polygon)
            else:
                covered = geom_helpers.check_if_polys_cover_bb(selected_polys_geoseries, bb)
            if plot:
                from matplotlib import pyplot
                gdf = geopandas.GeoDataFrame(selected_polys_geoseries) # cast up to geodataframe for plotting features
                gdf['pair_id'] = selected_polys_geoseries.index.values
                gdf.geometry = gdf.geometry.boundary
                gdf.plot(column='pair_id', legend=True, legend_kwds={'loc': 'center left', 'bbox_to_anchor': (1, 0.5)})
                ax = pyplot.gca()
                title = 'Covering set search w/ ' + str(grid_n) + '^2 points\n'
                unique_poly_count = len(numpy.unique(selected_polys_array))
                title += 'selected {} pairs from {}'.format(unique_poly_count, len(self.pairs))
                if covered:
                    title += ': success '
                else:
                    title += ': fail'
                pyplot.title(title)
                ax.set_xlabel('Longitude (Moon 2000)')
                ax.set_ylabel('Latitude (Moon 2000)')
                for point, selected_poly in zip(points, selected_polys_array):
                    if numpy.isnan(selected_poly):
                        ax.text(point.x, point.y, 'NaN')
                    else:
                        ax.text(point.x, point.y, int(round(selected_poly)))

                # Plot the grid points
                ax.plot([pt.x for pt in points], [pt.y for pt in points],'k.')

                # Plot the search polygon or bounding box
                if clip_to_polygon:
                    clip_poly_gdf = geopandas.GeoDataFrame()
                    clip_poly_gdf.geometry = [clip_to_polygon.boundary]
                    clip_poly_gdf.plot(ax=ax)
                else:
                    ax.plot(*bb.boundary.xy, color='red')
                pyplot.show()
            grid_n += grid_n_step

            if grid_n > grid_n_limit:
                break
        if covered:
            self.bb_covering_pairs = selected_polys_geoseries
            return selected_polys_geoseries
        else:
            return False

    def plot(self):
        from matplotlib import pyplot
        self.pairs.plot(edgecolor='grey')
        pyplot.show()

    def pairs_json(self):
        pair_ids = self.pairs.index.drop_duplicates()
        pairs_dict = [
            {'left': f'{pair_id.split("xx")[0]}',
             'right': f'{pair_id.split("xx")[1]}'}
            for pair_id in pair_ids
        ]
        return json.dumps(list(pairs_dict))

def trajectory(trajectory_csv, plot=False, find_covering=False, verbose=False):
    """
    Find stereo pairs beneath a trajectory of points

    :param trajectory_csv: Path to a comma separated values file in lat lon format, with header: point, lat, lon
    :param plot: Whether to output a plot of the pairs
    :param find_covering: Whether to search for a minimal set of pairs covering the trajectory. Otherwise, outputs all
    pairs that have good sun and spacecraft geometry.
    :return: A StereoPairSet
    """
    # TODO: implement plotting
    imgs = find_NACs_under_trajectory(csv_file_path=trajectory_csv)
    pairset = StereoPairSet(imgs)
    filtered_pairset = pairset.filter_sun_geometry().filter_small_overlaps()
    if find_covering:
        search_poly_shapely = wkt.loads(imgs.search_poly)
        filtered_pairset.pairs, stats = geom_helpers.covering_set_search(
            full_poly_set=filtered_pairset.pairs,
            search_poly=search_poly_shapely,
            plot=plot,
            verbose=False
        )
    print(filtered_pairset.pairs_json())
    return filtered_pairset

def bounding_box(*, west, east, south, north, plot=False, find_covering=True, return_pairset=False, verbose=False):
    """
    Find stereo pairs that fill a given bounding box

    :param plot:
    :param find_covering: Whether to search for a minimal set of pairs covering the bounding box. Otherwise, outputs all
    pairs that have good sun and spacecraft geometry.
    :return: A StereoPairSet
    """
    search_poly_shapely = geom_helpers.corners_to_quadrilateral(west, east, south, north)
    imgs = ImageSearch(polygon=wkt.dumps(search_poly_shapely))
    pairset = StereoPairSet(imgs)
    filtered_pairset = pairset.filter_sun_geometry().filter_small_overlaps()
    if find_covering:
        search_poly_shapely = wkt.loads(imgs.search_poly)
        filtered_pairset.pairs, stats = geom_helpers.covering_set_search(
            full_poly_set=filtered_pairset.pairs,
            search_poly=search_poly_shapely,
            plot=plot,
            verbose=False
        )
    print(filtered_pairset.pairs_json())
    if return_pairset:
        return filtered_pairset

if __name__ == '__main__':
    import clize, json
    clize.run(bounding_box, alt=trajectory)