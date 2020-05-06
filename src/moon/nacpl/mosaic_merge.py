"""
This script exists to translate arguments from the JSON format which Argo workflow passes them in to the format that
Ames Stereo Pipeline dem_merge expects
"""

import subprocess
from clize import run
import json
from os import path
from glob import glob

def mosaic_name(pairs_param):
    """
    Generates a filename for the mosaic. Concatenating the pair names would be very long so instead we combine the last
    four numbers of the product_id's.
    """
    return ''.join(
        [
            f'{pair["left"][-5:-1]}-{pair["right"][-5:-1]}_'
            for pair in pairs_param
        ]
    )[:-1]


def mosaic_merge(pairs_param, output_type, data_dir, output_dir):
    """
    Merge stereo pair output into a DEM mosaic (using ASP's dem_mosaic) or orthomosaic (using Orfeo Toolbox's Mosaic).

    :param pairs_param:
    :param output_type:
    :param data_dir: Where to look for source images
    :param output_dir: Where to output the mosaic
    :return:
    """
    output_type = output_type.upper()
    pairs_param = json.loads(pairs_param)
    output_prefix = f'{output_dir}/{mosaic_name(pairs_param)}'
    existing_file = glob(f'{output_prefix}*{output_type}.tif')
    print(f'Looking for {output_prefix}*{output_type}.tif')
    if not existing_file:
        pairs = [f'{data_dir}/{pair["left"]}xx{pair["right"]}-median-{output_type}.tif' for pair in pairs_param]
        pairs = [pair for pair in pairs if path.exists(pair)]
        if output_type == 'DEM':
            args = ['dem_mosaic'] + pairs + ['-o', output_prefix]
            args_str = ' '.join(args)
            print(f'running dem_mosaic {args_str}')
            subprocess.run(['dem_mosaic'] + pairs + ['-o', output_prefix])
        elif output_type == 'DRG':
            args = ['otbcli_Mosaic', '-il'] + pairs + ['-out', output_prefix + '-median-DRG.tif']
            args_str = ' '.join(args)
            print(f'running otbcli_Mosaic {args_str}')
            subprocess.run(
                ['otbcli_Mosaic', '-il'] +
                pairs +
                ['-comp.feather', 'slim', '-comp.feather.slim.exponent', '1', '-comp.feather.slim.length', '0.1'] +
                ['-harmo.method', 'band', '-harmo.cost', 'rmse'] +
                ['-nodata', '-9999', '-out', output_prefix + '-median-DRG.tif']
            )
    else:
        print(f'Skipping mosaic generation because {existing_file[0]} already exists')


if __name__ == '__main__':
    run(mosaic_merge)
