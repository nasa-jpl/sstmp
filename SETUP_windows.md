# Setup example on Windows 10

## Requirements
Admin access to a Windows 10 system. Instructions were tested on Windows build 2004.

## Setup the NAC Mosaic Pipeline
1. Install Docker Desktop
1. Enable Docker Desktop kubernetes
1. Download skaffold from https://storage.googleapis.com/skaffold/releases/v1.8.0/skaffold-windows-amd64.exe and install
1. Clone the Trek git repository

    `git clone git@github.com:nasa-jpl/sstmp.git`
1. Change directories into where skaffold.yaml is

    `cd sstmp/src`

1. Use skaffold to build and start the app

    `C:\whereYourDownloadsGo\skaffold-windows-amd64.exe run`

Now you are ready to [create your first mosaic](README_SSTMP.md#creating_a_mosaic).