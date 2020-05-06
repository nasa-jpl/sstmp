# CLI tool for downloading NAC specified by product ID

from clize import run
from urllib import request
import json
import wget

def get_nac_url(product_id: str):
    """
    Given a NAC product id, query the Washington University in St. Louis Orbital Data Explorer APO, and return a URL
    from which that NAC can be downloaded.

    :param product_id: PDS id of a NAC, for example M1134059748RE
    :return: URL
    """
    query_url = f'https://oderest.rsl.wustl.edu/live2/?query=product&PDSID={product_id}&results=f&output=json'
    resp = request.urlopen(url=query_url)
    resp = json.loads(resp.read())
    return resp['ODEResults']['Products']['Product']['Product_files']['Product_file'][0]['URL']

def download_NAC_image(product_id, download_dir):
    """
    Download a NAC by its product id.

    :param product_id: PDS id of a NAC, for example M1134059748RE
    :param download_dir: Directory into which to place the downloaded file
    """
    url = get_nac_url(product_id)
    wget.download(url=url, out=download_dir, bar=None)

if __name__ == '__main__':
    run(download_NAC_image)