#!/usr/bin/env python

from os import path
from clize import run

def download_LOLA_for_NAC_pair(left_nac, right_nac=None, nac_dir='/data/nac'):
    """
    Function that downloads Lunar Orbital Laser Altimeter (LOLA) Reduced Data Records (RDR) for a given pair of LRO NAC
    paths. If no right_nac is given, will retrieve LOLA data for bounds of left_nac only.

    For a pair, the download will be saved to a file [nac_dir]/[left pair id]xx[right pair id]_lola.csv

    :param left_nac: Path to a map-projected NAC file in ISIS .cub format
    :param right_nac: Path to a map-projected NAC file in ISIS .cub format
    :return: Full path of downloaded LOLA EDR .csv
    """
    from pysis.isis import getkey
    from pysis.exceptions import ProcessError
    left_file_path = path.join(nac_dir, left_nac)
    try:
        left_bounds = (
            getkey(from_=left_file_path, grpname='Mapping', keyword='MinimumLongitude').strip(),
            getkey(from_=left_file_path, grpname='Mapping', keyword='MinimumLatitude').strip(),
            getkey(from_=left_file_path, grpname='Mapping', keyword='MaximumLongitude').strip(),
            getkey(from_=left_file_path, grpname='Mapping', keyword='MaximumLatitude').strip()
        )
        if right_nac:
            right_file_path = path.join(nac_dir, right_nac)
            right_bounds = (
                getkey(from_=right_file_path, grpname='Mapping', keyword='MinimumLongitude').strip(),
                getkey(from_=right_file_path, grpname='Mapping', keyword='MinimumLatitude').strip(),
                getkey(from_=right_file_path, grpname='Mapping', keyword='MaximumLongitude').strip(),
                getkey(from_=right_file_path, grpname='Mapping', keyword='MaximumLatitude').strip()
            )
            lola_filename = path.join(nac_dir, f'{left_nac.split(".")[0]}xx{right_nac.split(".")[0]}_lola.csv')
        else:
            right_bounds = [None] * 4
            lola_filename = path.join(nac_dir, f'{left_nac.split(".")[0]}_lola.csv')
        minlon, minlat = [
            right_bound if float(right_bound) < float(left_bound)
            else left_bound
            for right_bound, left_bound
            in zip(right_bounds[0:2], left_bounds[0:2])
        ]
    except ProcessError as e:
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)

    maxlon, maxlat = [
        right_bound if float(right_bound) > float(left_bound)
        else left_bound
        for right_bound, left_bound
        in zip(right_bounds[2:4], left_bounds[2:4])
    ]
    minlon, minlat, maxlon, maxlat = [float(val) for val in (minlon, minlat, maxlon, maxlat)]

    download_LOLA_by_bounds(minlon=minlon, minlat=minlat, maxlon=maxlon, maxlat=maxlat, lola_filename=lola_filename)

def download_LOLA_by_bounds(minlon, minlat, maxlon, maxlat, save_dir='/data/nac', lola_filename=None):
    """
    Function that downloads Lunar Orbital Laser Altimeter (LOLA) Raw Data Records (RDR) for a given bounding box.

    Uses the Planetary Data System Geosciences Node's Granular Data System API. More info at:
     https://oderest.rsl.wustl.edu/GDS_REST_V2.0.pdf

    :param minlon: Western edge of search bounding box (0 to 360)
    :param minlat: Southern edge of search bounding box (-90 to 90)
    :param maxlon: Eastern edge of search bounding box (0 to 360)
    :param maxlat: Northern edge of search bounding box (-90 to 90)
    :return: Full path of downloaded LOLA .csv
    """
    import requests
    api_url = 'https://oderest.rsl.wustl.edu/livegds/'
    # API details available at https://oderest.rsl.wustl.edu/GDS_REST_V2.0.pdf
    params = {
                  'query': 'lolardr', 'results': 't', 'output': 'json',
                  'maxlat': maxlat, 'minlat': minlat,
                  'westernlon': minlon, 'easternlon': maxlon
              }
    resp = requests.get(api_url, params)
    file_resps = resp.json()['GDSResults']['ResultFiles']['ResultFile']
    for file_resp in file_resps:
        file_url = file_resp['URL']
        if file_url.endswith('.csv'):
            with open(path.join(save_dir, lola_filename), 'wb') as download_file:
                file_content = requests.get(file_url).content
                download_file.write(file_content)

if __name__ == '__main__':
    run(download_LOLA_for_NAC_pair)