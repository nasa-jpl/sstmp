# Dockerfile for SST Mosaic Pipeline lunar processing backend
# Aaron Curtis, Dec 2019

FROM ubuntu:18.04
SHELL ["/bin/bash", "-c"]

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get --allow-insecure-repositories update
RUN apt-get install -y --allow-unauthenticated wget git rsync
RUN wget -nv https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
RUN bash Miniconda3-latest-Linux-x86_64.sh -b

# Install USGS ISIS
RUN apt-get install -y --allow-unauthenticated libglu1
ENV PATH="/root/miniconda3/bin:$PATH"
RUN conda create -n isis isis python=3.6 --channel usgs-astrogeology --channel conda-forge
ENV ISISROOT /root/miniconda3/envs/isis

# Copy minimal files required for ISIS LRO NAC processing
ENV ISISDATA /isisdata
ENV PATH $ISISROOT/bin:$PATH
RUN mkdir -p /isisdata/lro/kernels/pck /isisdata/lro/kernels/tspk /nacpl
COPY lro_isis_rsync_exclude /nacpl/
RUN rsync -az --exclude-from=/nacpl/lro_isis_rsync_exclude isisdist.astrogeology.usgs.gov::isis3data/data/base /isisdata

# Install Ames Stereo Pipeline
RUN apt-get install -y --allow-unauthenticated xorg-dev
RUN wget -nv https://github.com/NeoGeographyToolkit/StereoPipeline/releases/download/v2.6.2/StereoPipeline-2.6.2-2019-06-17-x86_64-Linux.tar.bz2
RUN tar xjf StereoPipeline-2.6.2-2019-06-17-x86_64-Linux.tar.bz2
ENV PATH /StereoPipeline-2.6.2-2019-06-17-x86_64-Linux/bin:$PATH
ENV PYTHONPATH /StereoPipeline-2.6.2-2019-06-17-x86_64-Linux/libexec:$PYTHONPATH

# Set up environment with GDAL etc
COPY nacpl_env.yml /nacpl/
RUN conda env create -f /nacpl/nacpl_env.yml
RUN echo "source activate nacpl_env" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH

# Install Orfeo Toolbox (OTB) for ortho mosaics
RUN apt-get install -y --allow-unauthenticated file
RUN wget -nv https://www.orfeo-toolbox.org/packages/OTB-7.2.0-Linux64.run; chmod +x ./OTB-7.2.0-Linux64.run; ./OTB-7.2.0-Linux64.run
# This works for now but might need to source otbenv.profile if we use features of OTB other than mosaic
ENV PATH /OTB-7.1.0-Linux64/bin:$PATH

# Download latest LRO cumulative index
RUN wget -nv http://lroc.sese.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/LROLRC_0042A/INDEX/{CUMINDEX.TAB,INDEX.LBL}

# Copy nacpl scripts
COPY nacpl /nacpl/
