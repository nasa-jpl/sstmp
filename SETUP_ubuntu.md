# Setup example on Ubuntu 18.04

## Requirements
Terminal access to an Ubuntu 18.04 system, with root permissions.

## Setup the NAC Mosaic Pipeline
1. Install docker
1. Install minikube
1. Install skaffold
1. Install git
1. Install argo cli
1. Start minikube, using Docker without virtual machines:

    `sudo -E minikube start --vm-driver=none --apiserver-ips 127.0.0.1 --apiserver-name localhost`
    
1. Set permissions so the current user can use minikube commands

    `sudo chown -R $USER $HOME/.kube $HOME/.minikube`
    
1. Clone the Trek git repository

    `git clone git@github.com:nasa-jpl/sstmp.git`
1. Change directories into where skaffold.yaml is

    `cd sstmp/src`
    
1. Use skaffold to build and start the app

    `skaffold run`

Now you are ready to [create your first mosaic](README_SSTMP.md#creating_a_mosaic).