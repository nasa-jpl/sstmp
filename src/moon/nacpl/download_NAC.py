# CLI tool for downloading NAC specified by product ID

from clize import run
from urllib import request
import json
import wget
from multiprocessing import Pool

# Ignore SSL certificate errors, necessary because docker Ubuntu 18.04 image doesn't like wustl.edu cert for some reason
import ssl

ssl._create_default_https_context = ssl._create_unverified_context


def download(arg):
    (product_id, download_dir) = arg
    url = get_nac_url(product_id)
    wget.download(url=url, out=download_dir)


def get_nac_url(product_id: str):
    """
    Given a NAC product id, query the Washington University in St. Louis Orbital Data Explorer APO, and return a URL
    from which that NAC can be downloaded.

    :param product_id: PDS id of a NAC, for example M1134059748RE
    :return: URL
    """
    query_url = f"https://oderest.rsl.wustl.edu/live2/?query=product&PDSID={product_id}&results=f&output=json"
    resp = request.urlopen(url=query_url)
    resp = json.loads(resp.read())
    nacurl = resp["ODEResults"]["Products"]["Product"]["Product_files"]["Product_file"][
        0
    ]["URL"]
    print(nacurl)
    return nacurl


def download_NAC_image(product_id_or_json: str, download_dir: str):
    """
    Download a NAC by its product id.

    :param product_id_or_json: PDS id of a NAC, for example M1134059748RE
    :param download_dir: Directory into which to place the downloaded file
    """
    if product_id_or_json.endswith(".json"):  # json file path
        with open(product_id_or_json) as json_file:
            data = json.load(json_file)
            print(data)
            product_id_list = []
            for pair in data:
                product_id_list.append(pair["left"])
                product_id_list.append(pair["right"])
    else:  # product id
        product_id_list = [product_id_or_json]

    # iterate over set(product_id_list) so that products are only downloaded once
    args = [(product_id, download_dir) for product_id in set(product_id_list)]
    with Pool(8) as p:
        p.map(download, args)


if __name__ == "__main__":
    run(download_NAC_image)
