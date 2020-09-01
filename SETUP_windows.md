# Setup example on Windows 10

## Requirements
Admin access to a Windows 10 system. Instructions were tested on Windows build 2004.

## Setup the NAC Mosaic Pipeline
1. Install Docker Desktop
1. Enable Docker Desktop kubernetes
1. Download skaffold from https://storage.googleapis.com/skaffold/releases/v1.8.0/skaffold-windows-amd64.exe and install
1. Clone the Trek git repository

    `git clone -b argo https://code.jpl.nasa.gov/lmmpteam/TrekDataPrep.git`
1. Change directories into where skaffold.yaml is

    `cd TrekDataPrep\moon\NACpipeline`

1. Manually install Argo custom resource definitions, for complicated reasons. Hopefully this step can be removed.

    `kubectl apply -k https://github.com/argoproj/argo/manifests/base/crds/minimal`, 
    
1. Use skaffold to build and start the app

    `C:\whereYourDownloadsGo\skaffold-windows-amd64.exe run`

Now you are ready to [create your first mosaic](README_SSTMP.md#creating_a_mosaic).