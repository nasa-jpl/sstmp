import 'ol/ol.css'
import {Map, View} from 'ol'
import {Tile as TileLayer, Vector as VectorLayer} from 'ol/layer'
import {XYZ, Vector as VectorSource} from 'ol/source'
import {DragBox} from 'ol/interaction'
import {defaults as defaultControls} from 'ol/control';
import MousePosition from 'ol/control/MousePosition' 
import {createStringXY} from 'ol/coordinate'
import {Feature} from 'ol'
import {platformModifierKeyOnly} from 'ol/events/condition';

let mosaicGoal
const boxDrawSource = new VectorSource({wrapX: false})
const boxDrawLayer = new VectorLayer({source: boxDrawSource})
const moonBaseMap = new TileLayer({
    source: new XYZ({
        url: 'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png'
    })
})


const map = new Map({
    target: 'map',
    layers: [
        moonBaseMap, boxDrawLayer
    ],
    view: new View({
        center: [0, 0],
        zoom: 0        
    })
});


const dragBox = new DragBox({condition: platformModifierKeyOnly})
const mousePositionControl = new MousePosition({
    coordinateFormat: createStringXY(4),
    projection: 'EPSG:4326'
})

map.addControl(mousePositionControl)
map.addInteraction(dragBox)

dragBox.on('boxend', (evt)=>{
    mosaicGoal = evt.target.getGeometry().clone().transform('EPSG:3857','EPSG:4326')
    console.log(boxDrawSource)
    const mosaicExtent = mosaicGoal.getExtent()
    if (confirm(`Begin processing mosaic ${mosaicExtent.map((inp)=>inp.toPrecision(4))} ?`)){
        createMosaic(mosaicExtent)
        boxDrawSource.addFeature(new Feature({geometry: evt.target.getGeometry()}))
    }
})

const createMosaic = (mosaicExtent) => {
    const precision = 6
    // First, download the workflowtemplate for mosaics
    fetch('/api/v1/workflow-templates/default/nac-stereo-wftmpl').then(function (response) {
        return response.json();
    }).then((tmpl)=>{
        tmpl.spec.arguments.parameters = [
            {name: 'west', value: mosaicExtent[0].toPrecision(precision)},
            {name: 'south', value: mosaicExtent[1].toPrecision(precision)},
            {name: 'east', value: mosaicExtent[2].toPrecision(precision)},
            {name: 'north', value: mosaicExtent[3].toPrecision(precision)},
        ]
        submitMosaicWorkflow(tmpl)
        updateMosaicWorkflowList()
    })
}

const updateMosaicWorkflowList = () => {
    const mosaicsList = document.getElementById('workflow-list-content')
    fetch('/api/v1/workflows/default')
        .then(response => response.json())
        .then(workflows => {
            mosaicsList.innerHTML = ''
            workflows.items.map((wf)=>{
                const wfp = document.createElement('li')
                const wfLink = document.createElement('a')
                wfLink.href = `/workflows/${wf.metadata.namespace}/${wf.metadata.name}`
                wfLink.innerText = `${wf.metadata.name}, ${wf.status.phase}`
                wfp.appendChild(wfLink)
                mosaicsList.appendChild(wfp)
            }
            )})
}

const submitMosaicWorkflow = (template) => {
    const workflowSpec = {
        "metadata":{
            "generateName": template.metadata.generateName,
            "namespace": template.metadata.namespace
        },
        "spec": template.spec
    }
    const workflowString = JSON.stringify({"workflow": workflowSpec})
    fetch("http://acdesk.jpl.nasa.gov/api/v1/workflows/default", {
        "headers": {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache"
        },
        "referrer": "http://acdesk.jpl.nasa.gov/workflows?new=%7B%7D",
        "referrerPolicy": "no-referrer-when-downgrade",
        "body": workflowString,
        "method": "POST",
        "mode": "cors",
        "credentials": "include"
    })
        .then(response => response.json())
        .then(data => console.log(data))
}

updateMosaicWorkflowList()