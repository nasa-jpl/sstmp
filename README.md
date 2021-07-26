# Solar System Treks Mosaic Pipeline (SSTMP)

### Contents
1. [Description](#description)
2. [Requirements](#requirements)
3. [Setup](#setup)
4. [Creating a mosaic](#creating_a_mosaic)

## Description

SSTMP creates high-resolution lunar DEMs and orthoimage mosaics of Earth's moon for requested areas. Given a bounding box, it will select, fetch, ingest, stereo reconstruct, and merge raw imagery from the Lunar Reconnaissance Orbiter's (LRO) Narrow Angle Camera (NAC) to make your mosaic. It can be configured to use any number of real or virtual computers for processing. NAC Mosaic Pipeline uses laser altimeter data from LRO's Lunar Orbiter Laser Altimeter (LOLA) for alignment before merging the mosaics.

SSTMP includes:
 - An Argo workflow that supervises all of the processing for a stereo (nac-mos-stereo.yaml) or mono (nac-mos-mono.yaml) mosaic.
 - A Dockerfile defining a container which can do any of the processing steps (Dockerfile)
 - A python package with scripts needed for processing (nacpl/)
 - A conda environment needed for processing (nacpl_env.yml)
 - A Skaffold configuration for setting everything up (skaffold.yaml)
 
Development goals of the project are:
 - In the near term, SSTMP should:
   - Be easy to set up and run on any computer or cluster
   - Produce a reasonable mosaic from no user input other than requested bounding box, if sufficient data exists
   - Be flexible for cases where defaults don't result in good output
 - In the medium term:
   - NAC Mosaic Pipeline should provide rigorous error analyses
 
## Requirements
 - Any Kubernetes cluster. This can be minikube running on a single machine / node, a cloud service such as Amazon EKS, or your own custom cluster. [k3d](https://github.com/rancher/k3d) is recommended as a quick way to set up Kubernetes.
 - Nginx ingress setup on your kubernetes cluster. For minikube, this means running `minikube addons enable ingress`. 
 - A [Skaffold](https://skaffold.dev/docs/install/) installation that talks to your Kubernetes cluster
 - [Kustomize installed](https://github.com/kubernetes-sigs/kustomize/blob/master/docs/INSTALL.md) in your PATH. Unfortunately this needs to be kustomize 3, because of [this regression](https://github.com/kubernetes-sigs/kustomize/issues/3675) in kustomize 4.
 - A container image registry to which you have write access. You can set up a private registry using `docker run -d -p 5000:5000 --restart=always --name sstmp-reg registry:2` and then specify it using `--default-repo=localhost:5000` when the installation step using `skaffold` below

Internally, SSTMP uses a slew of free and open source programs, including:
 - USGS ISIS
 - Ames stereo pipeline (ASP)
 - Geopandas
 - GDAL
 - Orfeo toolbox

## Setup
If you already have the [requirements](#requirements),
1. Clone this repository
1. Change to the directory containing `skaffold.yaml` : `cd src`
1. Configure your storage settings. Open `volumes-example.yaml` in an editor, follow instructions in the comments, and save it as `volumes.yaml`.
1. Install SSTMP: run `skaffold run --status-check`

Otherwise, you may want to follow the [more detailed instructions which start from a bare Ubuntu installation](SETUP_ubuntu.md). 

<a id="creating_a_mosaic" name="creating_a_mosaic"></a>
## Creating a lunar mosaic

### Using the SSTMP web interface

Please see this video:

[<img src="https://img.youtube.com/vi/HfhUU9Abe4c/hqdefault.jpg" width="50%">](https://vimeo.com/457701800)


### Using the command line interface

Let's say you want a DEM and orthoimage mosaic of a bounding box which goes from 25.8 degrees easting to 25 degrees easting, and from 45 degrees north to 45.8 degrees north.

After following [setup](#setup) above, Run `argo submit NAC_pl_workflow.yaml -p east=25 -p west=25.8 -p south=45 -p north=45.8` . 

You can monitor the progress of the mosaic creation using the map interface which will be running at `http://yourcluster/moon`, or the Argo interface at `http://yourcluster/workflows`, where `yourcluster` is the ip address or hostname of your cluster master node.

## History

SSTMP grew out of work at JPL primarily by Marshall Trautman, Charles Nainan, Natalie Gallegos. The Trek Team maintained
an internal repo called "TrekDataPrep" which was a precursor of SSTMP. Aaron Curtis joined the project in late 2019,
re-imagined and re-wrote TrekDataPrep as a system of Argo Workflows, and obtained permission from JPL to open source the
project. For file size and security reasons, repository history before 2020-05-06 was removed before the first release
of SSTMP. Although 98 of the 400 commits in the repo were preserved, the commit hashes were changed.