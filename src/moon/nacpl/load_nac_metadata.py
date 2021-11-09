"""
Loads LROC NAC metadata and footprints from local
"""

import typing
from pandas.io.parsers import TextFileReader

# Read column descriptions from CUMINDEX.LBL
# this was downloaded from http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0040C/INDEX/
lblfilepath = r'/INDEX.LBL'
indfilepath = r'/CUMINDEX.TAB'
footprintfileglob = r'/moon_lro_lroc_edrnac_ga/*.shp'

CHUNK_SIZE = 5000  # lines


def load_nac_index(lblfilepath=lblfilepath, indfilepath=indfilepath, chunksize=CHUNK_SIZE) -> typing.Union[
    TextFileReader]:
    import pandas
    import pvl
    with open(lblfilepath, 'r') as lblfile:
        lblstr = lblfile.read()
        lblpvl = pvl.loads(lblstr)

        col_pvl = lblpvl['INDEX_TABLE'].getlist('COLUMN')
        col_list = [col['NAME'].lower() for col in col_pvl]

        nac_index = pandas.read_csv(indfilepath, header=None, names=col_list, chunksize=chunksize)
    return nac_index


def load_nac_footprints(footprintfileglob=footprintfileglob):
    import geopandas
    import glob
    footprint_data = [geopandas.read_file(shpfile) for shpfile in glob.glob(footprintfileglob)]
    return footprint_data
