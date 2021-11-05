# Dockerfile for SST Mosaic Pipeline lunar processing backend
# Aaron Curtis, Dec 2019

FROM ubuntu:20.04
SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get --allow-insecure-repositories update
RUN apt-get install -y --allow-unauthenticated wget git rsync
RUN wget -nv https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash Miniconda3-latest-Linux-x86_64.sh -b -p /opt/miniconda3
RUN chmod -R 777 /opt/miniconda3

# Install USGS ISIS and Ames Stereo Pipeline
RUN apt-get install -y --allow-unauthenticated libglu1
ENV PATH="/opt/miniconda3/bin:$PATH"
RUN conda create -n isis python=3.6; \
    source activate isis; \
    conda config --env --add channels conda-forge; \
    conda config --env --add channels usgs-astrogeology; \
    conda config --env --add channels nasa-ames-stereo-pipeline; \
    conda install stereo-pipeline==2.7.0

ENV ISISROOT /opt/miniconda3/envs/isis

# Copy minimal files required for ISIS LRO NAC processing
ENV ISISDATA /isisdata

#maybe don't need to add to path if using conda activate
ENV PATH $ISISROOT/bin:$PATH
RUN mkdir -p /isisdata/lro/kernels/pck /isisdata/lro/kernels/tspk /nacpl
COPY lro_isis_rsync_exclude /nacpl/
RUN rsync -az --exclude-from=/nacpl/lro_isis_rsync_exclude isisdist.astrogeology.usgs.gov::isis3data/data/base /isisdata
RUN rsync -az --exclude 'wac*' --exclude 'WAC*' isisdist.astrogeology.usgs.gov::isis3data/data/lro/calibration /isisdata/lro/

# Download latest LRO cumulative index
RUN wget -nv http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0042A/INDEX/{CUMINDEX.TAB,INDEX.LBL}

# Install Orfeo Toolbox (OTB) for ortho mosaics
RUN apt-get install -y --allow-unauthenticated file
RUN wget -nv https://www.orfeo-toolbox.org/packages/archives/OTB/OTB-7.2.0-Linux64.run; chmod +x ./OTB-7.2.0-Linux64.run; ./OTB-7.2.0-Linux64.run
# This works for now but might need to source otbenv.profile if we use features of OTB other than mosaic
ENV PATH /OTB-7.2.0-Linux64/bin:$PATH

## Set up environment with GDAL etc
COPY nacpl_env.yml /nacpl/
RUN conda env create -f /nacpl/nacpl_env.yml
RUN echo "source activate isis" > ~/.bashrc
RUN echo "source activate --stack nacpl_env" > ~/.bashrc

# Copy nacpl scripts
COPY nacpl /nacpl/
COPY setup.py /
RUN source activate isis; source activate --stack nacpl_env; python setup.py install
COPY IsisPreferences $ISISROOT