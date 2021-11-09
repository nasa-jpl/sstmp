"""
Find stereo pair candidates in bounding box
Aaron Curtis
2019-10-15
"""

# TODO check that none of the filters modify self.pairs when inplace is False
# TODO add type hinting
# TODO make addition of inplace parameter into a decorator


from nacpl import geom_helpers, load_nac_metadata
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely import wkt
import geopandas, pandas
import re
import numpy
import urllib

projections = {
    # IAU2000:30101
    'ec': '+proj=longlat +a=1737400 +b=1737400 +no_defs',
    # IAU2000:30118
    'np': '+proj=stere +lat_0=90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m +no_defs',
    # Use IAU2000:30120
    'sp': '+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m +no_defs'
}

pandas.options.mode.chained_assignment = None

lblfilepath = r'/INDEX.LBL'
indfilepath = r'/CUMINDEX.TAB'


def nac_url_to_id(url: str) -> str:
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
                               buffersize: float = 0.5,
                               tolerance: float = 0.05) -> 'ImageSearch':
    """
    Finds NAC images to cover all points in csv_file

    :param csv_file_path: Path to a comma separated values file in lat lon format, with header: point, lat, lon
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
    """

    def __init__(self, *args, **kwargs):
        self.search_args = args
        self.search_kwargs = kwargs
        if 'polygon' in kwargs.keys():
            self.search_poly = kwargs['polygon']
            self.results = self._search_from_poly(*args, **kwargs)
        else:
            self.results = self._search_from_bb(*args, **kwargs)

    @staticmethod
    def _search_from_poly(polygon: str,
                          indfilepath=indfilepath,  # TODO need better solution than hardcoding path to local files
                          lblfilepath=lblfilepath,
                          projection: str = 'ec',
                          verbose: bool = False
                          ):
        """
        :param str projection: The projection to use. Should be 'ec' for lat / lon equidistant cylindrical, 'sp' for
        south polar, 'np' for north polar. 
        """
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
        footprints = pandas.DataFrame(resp['ODEResults']['Products']['Product'])
        # lowercase all column names for ease of joining from different APIs
        footprints.columns = [col.lower() for col in footprints.columns]
        footprints.set_index('pdsid', inplace=True)

        filtered = []
        chunks_metadata = load_nac_metadata.load_nac_index(indfilepath=indfilepath, lblfilepath=lblfilepath)
        for chunk_metadata in chunks_metadata:  # iterate over chunks instead of loading all CSV into RAM
            chunk_metadata.product_id = chunk_metadata.product_id.apply(str.strip)
            chunk_metadata.set_index('product_id', inplace=True)
            chunk_footprints = footprints.join(chunk_metadata, how='inner', lsuffix='_ode', rsuffix='')

            # For the columns that were in common between CUMINDEX.TAB and ODE REST API
            # remove the ODE ones and keep the ones from CUMINDEX.TAB
            chunk_footprints = chunk_footprints.loc[:,
                         [col for col in chunk_footprints.columns if not col.endswith('_ode')]
                         ]
            chunk_footprints = chunk_footprints.apply(to_numeric_or_date)

            crs = projections[projection]
            if projection == 'ec':
                # Use IAU2000:30101
                crs = '+proj=longlat +a=1737400 +b=1737400 +no_defs'
                chunk_footprints.footprint_geometry = chunk_footprints.footprint_geometry.apply(wkt.loads)
            elif projection == 'sp':
                # Use IAU2000:30120
                crs = '+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m +no_defs'
                chunk_footprints.footprint_geometry = chunk_footprints.footprint_sp_geometry.apply(wkt.loads)
            elif projection == 'np':
                # Use IAU2000:30118
                crs = '+proj=stere +lat_0=90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m +no_defs'
                chunk_footprints.footprint_geometry = chunk_footprints.footprint_np_geometry.apply(wkt.loads)

            chunk_footprints = geopandas.GeoDataFrame(chunk_footprints, geometry='footprint_geometry')
            chunk_footprints.crs = crs
            chunk_footprints.geometry = chunk_footprints.footprint_geometry

            # Upcast from shapely LineString to shapely Polygon
            def polygonize(geom):
                if geom.geom_type == 'GeometryCollection':
                    try:
                        return MultiPolygon(geom)
                    except TypeError:
                        print(f'Problem geometry: {geom} dropped')
                        return None
                else:
                    try:
                        return Polygon(geom)
                    except NotImplementedError:
                        print(f'Problem geometry: {geom} dropped')
                        return None

            chunk_footprints.footprint_geometry = chunk_footprints.footprint_geometry.apply(
                polygonize
            )
            chunk_footprints.crs = '+proj=longlat +a=1737400 +b=1737400 +no_defs'
            filtered.append(chunk_footprints)
        return pandas.concat(filtered).dropna()

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

    def __init__(self, imagesearch: ImageSearch = None, pairs=None, projection: str = 'ec'):
        # If StereoPairSet is instantiated with another StereoPairSet, copy the pairs
        if pairs is not None:
            self.pairs = pairs
        elif imagesearch is not None:
            gdf = imagesearch.results.dropna()
            gdf[
                'prod_id'] = gdf.index  # Store index (product id) in column so that it's preserved in spatial join operation
            self.pairs = geopandas.overlay(gdf, gdf, how='union', keep_geom_type=True)
            # If we're in lat lon, then need to convert to meters before calculating area
            if projection == 'ec':
                pairs_eqc = self.pairs.to_crs(
                    "+proj=eqc +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +a=1737400 +b=1737400 +units=m +no_defs"
                )
            self.pairs['area_m2'] = pairs_eqc.area  # Store area as column before sorting (could use key fn instead...)
            self.pairs.sort_values('area_m2', ascending=False, inplace=True)
            self.filter_unique(
                inplace=True)  # TODO pair_id is created inside this method call -- maybe not the best place for that
            self.pairs.set_index('pair_id', inplace=True)
            self.bb_covering_pairs = None
        else:
            raise TypeError("Need either imagesearch or pairs argument to instantiate StereoPairSet")

    def filter_new_pairs(self, since, inplace: bool = True) -> 'StereoPairSet':
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

    def filter_date_range(self, startime, endtime, inplace: bool = True) -> 'StereoPairSet':
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

    def filter_sufficient_convergence(self, min_convergence: float = 2, inplace: bool = True) -> 'StereoPairSet':
        """
        Removes stereo pairs which have an emission angle difference of less than min_convergence degrees.
        :param inplace: Replace .pairs of this StereoPairSet instance with the filtered version
        :param min_convergence: Convergence angle beneath which to remove pair
        :return: StereoPairSet with pairs that have insufficient convergence removed.
        """
        filtered_pairs = self.pairs[
            numpy.abs(self.pairs.emission_angle_1 - self.pairs.emission_angle_2) > min_convergence]
        if inplace:
            self.pairs = filtered_pairs
        return StereoPairSet(pairs=filtered_pairs)

    def filter_sun_geometry(self, max_sun_azimuth_ground_difference: float = 20,
                            max_incidence_angle_difference: float = 20,
                            inplace: bool = True) -> 'StereoPairSet':
        """
        Removes stereo pairs which have incompatible sun geometry.
        :param max_sun_azimuth_ground_difference: Maximum sun azimuth difference, in degrees.
        :param max_incidence_angle_difference: Maximum sun incidence angle difference, in degrees.
        :param inplace: Replace .pairs of this StereoPairSet instance with the filtered version
        :return: StereoPairSet of pairs with bad sun geometry pairs removed.
        """
        big_incidence_diff = numpy.abs(
            self.pairs.incidence_angle_1 - self.pairs.incidence_angle_2) < max_incidence_angle_difference
        sub_solar_ground_az_1 = self.pairs.north_azimuth_1 - self.pairs.sub_solar_azimuth_1
        sub_solar_ground_az_2 = self.pairs.north_azimuth_2 - self.pairs.sub_solar_azimuth_2
        sub_solar_ground_az_diff = numpy.abs(sub_solar_ground_az_1 - sub_solar_ground_az_2)
        big_sunaz_diff = sub_solar_ground_az_diff < max_sun_azimuth_ground_difference
        filtered_pairs = self.pairs[big_incidence_diff & big_sunaz_diff]
        if inplace:
            self.pairs = filtered_pairs
        return StereoPairSet(pairs=filtered_pairs)

    def filter_small_overlaps(self, min_area: float = 50000000, inplace: bool = True) -> 'StereoPairSet':
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

    def filter_unique(self, inplace: bool = True) -> 'StereoPairSet':
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

    def filter_incidence(self, inplace: bool = True) -> 'StereoPairSet':
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

    def stereo_quality(self) -> pandas.DataFrame:
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

    def find_covering_set_poly(self, polygon: str, plot: bool = False):
        """
        Convenience wrapper for using find_covering_set with a search polygon which computes the bounding box for you

        :param plot: Toggle pair plot
        :param polygon: A polygon in which find_covering_set will search
        """
        # Convert from WKT string to shapely
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

    def plot(self) -> None:
        from matplotlib import pyplot
        self.pairs.plot(edgecolor='grey')
        pyplot.show()

    def pairs_json(self) -> str:
        pair_ids = self.pairs.index.drop_duplicates()
        pairs_dict = [
            {'left': f'{pair_id.split("xx")[0]}',
             'right': f'{pair_id.split("xx")[1]}'}
            for pair_id in pair_ids
        ]
        return json.dumps(list(pairs_dict))


def trajectory(trajectory_csv: str, plot: bool = False, find_covering: bool = False, verbose=False) -> 'StereoPairSet':
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


def bounding_box(*, west: float, east: float, south: float, north: float, plot: bool = False,
                 find_covering: bool = True,
                 return_pairset: bool = False, verbose=False) -> 'StereoPairSet':
    """
    Find stereo pairs that fill a given bounding box
    
    # :param west: Western limit of the box, in -180 to 180 longitude, positive east
    # :param east: Eastern limit of the box, in -180 to 180 longitude, positive east
    # :param south: Southern limit of the box, in -90 to 90 latitude, positive north
    # :param north: Northern limit of the box, in -90 to 90 latitude, positive north
    :param plot: Whether to plot the footprints of the selected images
    :param find_covering: Whether to search for a minimal set of pairs covering the bounding box. Otherwise, outputs all
    pairs that have good sun and spacecraft geometry.
    :return: A StereoPairSet
    """

    search_poly_shapely = geom_helpers.corners_to_quadrilateral(west, east, south, north, lonC0=True)
    imgs = ImageSearch(polygon=wkt.dumps(search_poly_shapely))
    pairset = StereoPairSet(imgs)
    if verbose:
        print(f"found {len(pairset.pairs.index)} pairs.")
    filtered_pairset = pairset.filter_sun_geometry()
    if verbose:
        print(f"found {len(filtered_pairset.pairs.index)} pairs after filtering out incompatible sun geometry.")
    filtered_pairset = filtered_pairset.filter_small_overlaps()
    if verbose:
        print(f"found {len(filtered_pairset.pairs.index)} pairs after filtering out insufficient overlaps.")
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
