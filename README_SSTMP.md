# Solar System Treks Mosaic Pipeline (SSTMP)

### Contents
1. [Description](#description)
2. [Requirements](#requirements)
3. [Setup](#setup)
4. [Creating a mosaic](#creating_a_mosaic)

## Description

SSTMP creates a high-resolution lunar DEM and orthoimage mosaic of Earth's moon for a requested area. Given a bounding box, it will select, fetch, injest, stereo reconstruct, and merge raw imagery from the Lunar Reconnaissance Orbiter's (LRO) Narrow Angle Camera (NAC) to make your mosaic. It can be configured to use any number of real or virtual computers for processing. NAC Mosaic Pipeline uses laser altimeter data from LRO's Lunar Orbiter Laser Altimeter (LOLA) for alignment before merging the mosaics.

SSTMP includes:
 - An Argo workflow that supervises all of the processing (NAC_pl_workflow.yaml)
 - A Dockerfile defining a container which can do any of the processing steps (Dockerfile)
 - A python package with scripts needed for processing (nacpl/)
 - A conda environment needed for processing (NAC_pl_env.yml)
 - A Skaffold configuration for setting everything up (skaffold.yaml)
 
Development goals of the project are:
 - Near term, SSTMP should:
   - Be easy to set up and run on any computer or cluster
   - Produce a reasonable mosaic from no user input other than requested bounding box, if sufficient data exists
   - Be flexible for cases where defaults don't result in good output
 - Medium term:
   - NAC Mosaic Pipeline should provide rigorous error analyses
 
## Requirements
 - Any Kubernetes cluster. This can be minikube running on a single machine / node, a cloud service such as Amazon EKS, or your own custom cluster. [k3d](https://github.com/rancher/k3d) is recommended as a quick way to set up Kubernetes.
 - A [Skaffold](https://skaffold.dev/docs/install/) installation that talks to your Kubernetes cluster

Internally, NAC Mosaic Pipeline uses a slew of free and open source programs, including:
 - USGS ISIS
 - Ames stereo pipeline (ASP)
 - Geopandas
 - GDAL
 - Orfeo toolbox

## Setup
If you already have the [requirements](#requirements),
1. Clone this repository
1. Change to the directory containing `skaffold.yaml` : `cd moon/NACpipeline/workflow` 
1. Install SSTMP: `skaffold run`

Otherwise, you may want to follow the [more detailed instructions which start from a bare Ubuntu installation](SETUP-minikube.md). 

<a id="creating_a_mosaic" name="creating_a_mosaic"></a>
## Creating a mosaic
Let's say you want a DEM and orthoimage mosaic of a bounding box which goes from 25.8 degrees easting to 25 degrees easting, and from 45 degrees north to 45.8 degrees north.

After following [setup](#setup) above, Run `argo submit NAC_pl_workflow.yaml -p east=25 -p west=25.8 -p south=45 -p north=45.8` . 

You can monitor the progress of the mosaic creation using the web user interface which will be running at `http://yourcluster:32019`, where `yourcluster` is the ip address or hostname of your cluster master node.
