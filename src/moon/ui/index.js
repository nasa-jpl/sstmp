import 'ol/ol.css'
import {Map, View} from 'ol'
import {Tile as TileLayer, Vector as VectorLayer} from 'ol/layer'
import {XYZ, Vector as VectorSource} from 'ol/source'
import {DragBox} from 'ol/interaction'
import {fromExtent} from "ol/geom/Polygon";
import MousePosition from 'ol/control/MousePosition' 
import {createStringXY} from 'ol/coordinate'
import {Feature} from 'ol'
import {boundingExtent} from 'ol/extent'
import {platformModifierKeyOnly} from 'ol/events/condition';
import {Fill, Stroke, Style, Text} from 'ol/style';

let mosaicGoal

// workflowData is an object to cache all of the app state. Its format is like:
// {workflowName: {metadata: ..., boundingBox: {east: 1, south: , west: , north: }, status: {...}}}
let workflowData = {}

const boxDrawSource = new VectorSource({wrapX: false}) 
const mosaicBBstyle = new Style({
    text: new Text({
        text: '',
        font: '50px sans-serif',
        placement: 'line'
    }),
    stroke: new Stroke({color: 'blue', width: 1})
}) 
const mosaicBBstyleWlabel = (feature, resolution) => {
    mosaicBBstyle.getText().setText(feature.get('name'))
    return mosaicBBstyle 
}
const boxDrawLayer = new VectorLayer({
    source: boxDrawSource,
    style: mosaicBBstyleWlabel
})
const moonBaseMap = new TileLayer({
    source: new XYZ({
        url: 'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png'
    })
})

// map setup
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
    })
}

const addListEntry = (workflow) => {
    const mosaicsList = document.getElementById('workflow-list-content')
    const wfli = document.createElement('li')
    const wfLink = document.createElement('a')
    wfLink.href = `/workflows/${workflow.metadata.namespace}/${workflow.metadata.name}`
    wfLink.target = '_blank'
    wfLink.innerText = `${workflow.metadata.name}, ${workflow.status.phase}`
    wfli.appendChild(wfLink)
    mosaicsList.appendChild(wfli)
}

const attachToWorkflowEvents = () => {
    const eventSource = new EventSource('http://acdesk.jpl.nasa.gov/api/v1/workflow-events/default')
    // receive the message and cache the important parts into workflowData
    eventSource.onmessage = (evt) => {
        const data = JSON.parse(evt.data)
        console.log(data)
        const wfName = data.result.object.metadata.name
        if (data.result.type == "DELETED"){
            delete workflowData[wfName]
        } else {
            const wfNodes = data.result.object.status.nodes
            const topNode = wfNodes[wfName]
            workflowData[wfName] = {
                metadata: data.result.object.metadata,
                boundingBox: arrayToObject(topNode.inputs.parameters),
                status: data.result.object.status
            }   
        }
        update()
    }
}

const clearMap = () => {
    boxDrawSource.clear()
}

const clearWFList = () => {
    const wfList = document.getElementById('workflow-list-content')
    wfList.innerHTML = ''
}

const update = () => {
    clearMap()
    clearWFList()
    for (const wfName in workflowData){
        const wf = workflowData[wfName]
        addBox(wf)
        addListEntry(wf)
    }
    console.log(map)
}

const arrayToObject = (arr) => {
    const obj = {}
    arr.map((el) => obj[el.name] = el.value)
    return obj
}

const addBox = (workflow) => {
    const extent = new boundingExtent([
        [workflow.boundingBox.west, workflow.boundingBox.south],
        [workflow.boundingBox.east, workflow.boundingBox.north],
    ])
    const newFeat = new Feature(fromExtent(extent).transform('EPSG:4326', 'EPSG:3857'))
    newFeat.set('name', workflow.metadata.name)
    boxDrawSource.addFeature(newFeat)
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

attachToWorkflowEvents()