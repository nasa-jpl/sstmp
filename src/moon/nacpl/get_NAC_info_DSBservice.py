#!/usr/bin/env python
""" 
=========================================================================================

Script to OROCS ASU DSBservic for image matches given a lat/lon bounding box using
 two points (lower left and upper right).

get_NAC_info_DSBservice.py M104511971RE

images = get_NAC_info_bbox_DSBservice(10,11,-.5,0.5)
for image in images:
    print image["product_id"],image["url"]

output:
  Found 46 images!!
M120965596RE http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0002/DATA/MAP/2010047/NAC/M120965596RE.IMG
M120965596LE http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0002/DATA/MAP/2010047/NAC/M120965596LE.IMG
M131575892LE http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0004/DATA/MAP/2010170/NAC/M131575892LE.IMG
M131575892RE http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0004/DATA/MAP/2010170/NAC/M131575892RE.IMG
M132766590RE http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0004/DATA/MAP/2010184/NAC/M132766590RE.IMG
M146913009RE http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0005/DATA/SCI/2010347/NAC/M146913009RE.IMG     
...
 =========================================================================================
"""
from bs4 import BeautifulSoup
import os, glob,time, sys, os, logging, traceback, itertools, math, getopt,urllib.request,urllib.error,urllib.parse
import subprocess

NAC_DSBService_KEYS =['instrument_host_id',
 'instrument_id',
 'original_product_id',
 'product_id',
 'product_version_id',
 'target_name',
 'orbit_number',
 'slew_angle',
 'mission_phase_name',
 'rationale_desc',
 'data_quality_id',
 'nac_preroll_start_time',
 'start_time',
 'stop_time',
 'spacecraft_clock_partition',
 'nac_spacecraft_clock_preroll_count',
 'spacecraft_clock_start_count',
 'spacecraft_clock_stop_count',
 'start_sclk_seconds',
 'start_sclk_ticks',
 'stop_sclk_seconds',
 'stop_sclk_ticks',
 'nac_line_exposure_duration',
 'wac_exposure_duraction',
 'nac_frame_id',
 'nac_dac_reset',
 'nac_channel_a_offset',
 'nac_channel_b_offset',
 'instrument_mode_code',
 'wac_instrument_mode_id',
 'wac_band_code',
 'wac_background_offset',
 'wac_filter_name',
 'wac_number_of_frames',
 'wac_interframe_time',
 'wac_interframe_code',
 'wac_mode_polar',
 'compand_select_code',
 'node_compression',
 'mode_test',
 'nac_temperature_scs',
 'nac_temperature_fpa',
 'nac_temperature_fpga',
 'nac_temperature_telescope',
 'wac_begin_temperature_scs',
 'wac_middle_temperature_scs',
 'wac_end_temperature_scs',
 'wac_begin_temperature_fpa',
 'wac_middle_temperature_fpa',
 'wac_end_temperature_fpa',
 'image_lines',
 'line_samples',
 'sample_bits',
 'scaled_pixel_width',
 'scaled_pixel_height',
 'resolution',
 'emission_angle',
 'incidence_angle',
 'phase_angle',
 'north_azimuth',
 'sub_solar_azimuth',
 'sub_solar_latitude',
 'sub_solar_longitude',
 'sub_spacecraft_latitude',
 'sub_spacecraft_longitude',
 'solar_distance',
 'solar_longitude',
 'center_latitude',
 'center_longitude',
 'upper_right_latitude',
 'upper_right_longitude',
 'lower_right_latitude',
 'lower_right_longitude',
 'lower_left_latitude',
 'lower_left_longitude',
 'upper_left_latitude',
 'upper_left_longitude',
 'spacecraft_altitude',
 'target_center_distance',
 'orbit_node',
 'lro_flight_direction']

def get_NAC_info_bbox_DSBservice(west, south, east, north, keys = NAC_DSBService_KEYS, verbose=True):

    url='http://trek.nasa.gov/moon/DSBservice/webapi/lroc/CUMINDEX/xml/EDR/?bbox=%s,%s,%s,%s'%(str(west),str(south),str(east),str(north))
    soup = BeautifulSoup(urllib.request.urlopen((url)).read(),"lxml")

    imageinfo= []
    download = 'http://lroc.sese.asu.edu/data/'
    
    for im  in soup.findAll('file_specification_name'):
        image = {}
        image['url'] = download + str(im.text)
        for key in keys:
            try:
                image[key] = str(im.find_next(key).text)
            except: pass
        image['product_id'] = str(im.find_next('product_id').text.split(" ")[0])
        #print str(im.text).split("/")[-1],str(im.find_next('product_id').text.split(" ")[0])
        #str(im.find_next('nac_temperature_scs').text)
        imageinfo.append(image)

    if verbose: 
        print("Found %d images!!"%(len(imageinfo)))
            
    return imageinfo

def get_NAC_info_id_DSBservice(product_id,keys = NAC_DSBService_KEYS, verbose=True):
    
    image = None
    url='http://trek.nasa.gov/moon/DSBservice/webapi/lroc/CUMINDEX/xml/%s'%(product_id)
    if verbose: 
        print("url: ",url)

    soup = BeautifulSoup(urllib.request.urlopen((url)).read(),"lxml")

    imageinfo= []
    download = 'http://lroc.sese.asu.edu/data/'
    print("Download base = ",download)
    print(soup)     
    for im  in soup.findAll('file_specification_name'):
        image = {}
        print("hello")
        print("Download url = ", download+str(im.text))
        image['url'] = download + str(im.text)
        for key in keys:
            try:
                image[key] = str(im.find_next(key).text)
            except: pass
        image['product_id'] = str(im.find_next('product_id').text.split(" ")[0])
        #print str(im.text).split("/")[-1],str(im.find_next('product_id').text.split(" ")[0])
        #str(im.find_next('nac_temperature_scs').text)
        imageinfo.append(image)
    if len(imageinfo) == 0:
        if verbose: print("Unable to find image for id: ",product_id)
    else:
        image = imageinfo[0]
        if verbose: 
            print("Found %d images!!"%(len(imageinfo)))

            for key,value in image.items():
                print(key,value)
    return image
    
    
def download_NAC_image(product_id,download_dir='/data/nac',verbose=True,uuid_prefix_length=6):
    start_time = time.time()
    print(uuid_prefix_length)
    product_id_noprefix = product_id[uuid_prefix_length:]
    image = get_NAC_info_id_DSBservice(product_id_noprefix, keys = NAC_DSBService_KEYS, verbose=True)
    print('downloading' + product_id_noprefix)
    print(image)
    if image is None:
        if verbose: print("Unable to find image for id: ",product_id)
        return image,-1
    os.chdir(download_dir)
    wget_results = subprocess.run(args=["wget", "--progress=dot:giga", "-c", image['url'], "-O", product_id + ".IMG"])
    if verbose:
        print("Downloading %s..." % (product_id))
        print(wget_results.returncode)
    elapsed = time.time() - start_time
    if verbose: print("Took %0.2f secs, " % (elapsed))

    return (image, wget_results.returncode)




def download_NAC_images(prod_list,download_dir='/data/nac',verbose=True):
    """
    Dwonload NAC images in list return imageinfo,ret
    > images, rets = download_NAC_images(list,download_dir=datadir,verbose=True)
    """
    results = [ download_NAC_image(prod,download_dir=download_dir,verbose=verbose) for prod in prod_list ]
    images  = [ result[0] for result in results ]
    rets    = [ result[1] for result in results ]
    return images,rets

def main(argv):
    download_NAC_image(product_id=argv, uuid_prefix_length=6)
if __name__ == "__main__":
    main(sys.argv[1:][0])
