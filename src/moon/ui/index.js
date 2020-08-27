import 'ol/ol.css'
import {Map, View} from 'ol'
import {DragBox} from 'ol/interaction'
import {fromExtent} from "ol/geom/Polygon";
import MousePosition from 'ol/control/MousePosition' 
import {createStringXY} from 'ol/coordinate'
import {Feature} from 'ol'
import {boundingExtent} from 'ol/extent'
import WKT from "ol/format/WKT";
import {
    hillshade,
    nomenclature,
    boxDrawLayer,
    boxDrawSource,
    nac_avail_tiles,
    nacFootprintsLayer,
    nacFootprintsSource,
    addMosaicJobListEntry,
    highlight
} from "./layers";
import {nacHist} from "./nac_hist";
import {workflowData, nacData, attachToWorkflowEvents} from "./rxdata";

let mosaicGoal

// map setup
export const moonmap = new Map({
    target: 'map',
    layers: [
        hillshade, nomenclature, boxDrawLayer, nac_avail_tiles, nacFootprintsLayer
    ],
    view: new View({
        center: [0, 0],
        zoom: 0        
    })
});

moonmap.on('rendercomplete', ()=>{
    if (document.getElementById('nac_avail').checked) {
        nacHist.update(0)
    }
})

const dragBox = new DragBox()
const mousePositionControl = new MousePosition({
    coordinateFormat: createStringXY(4),
    projection: 'EPSG:4326'
})

const layerSelector = document.getElementById('layer-selector')
const layerSelectionChbxs = [...document.querySelectorAll('input[name="layer-chbx"]')]
layerSelector.onclick = (evt) => {
    layerSelectionChbxs.map((chbx)=>{
        moonmap.getLayers().array_.map((layer)=>{
            if (chbx.id === layer.get('name')){
                layer.setVisible(chbx.checked)
                if (chbx.id === 'nac_avail'){
                    document.getElementById('nacAvailHist').style.display = (chbx.checked ? 'block' : 'none')
                }
            } 
        })
    })
}

moonmap.addControl(mousePositionControl)

moonmap.on('pointermove', (evt)=>{
    let newHighlight = null
    moonmap.forEachFeatureAtPixel(evt.pixel, (feat)=>{
        newHighlight = feat.id_
    })
    highlight(newHighlight)
    boxDrawSource.changed()
})

dragBox.on('boxend', (evt)=>{
    mosaicGoal = evt.target.getGeometry().clone().transform('EPSG:3857','EPSG:4326')
    console.log(boxDrawSource)
    const mosaicExtent = mosaicGoal.getExtent()
    if (confirm(`Begin processing mosaic ${mosaicExtent.map((inp)=>inp.toPrecision(4))} ?`)){
        createMosaic(mosaicExtent)
        boxDrawSource.addFeature(new Feature({geometry: evt.target.getGeometry()}))
    }
    mosaic_dropdown.value = 'navigate'
})

const mosaic_dropdown = document.getElementById('mosaic-type-select')
mosaic_dropdown.onchange = (evt) => {
    const instructions = document.getElementById('instructions').firstElementChild 
    if (['mono', 'stereo'].includes(evt.target.value)){
        moonmap.addInteraction(dragBox)
        instructions.innerHTML = 'Click and drag to create a mosaic'
    } else {
        moonmap.removeInteraction(dragBox)
        instructions.innerHTML = 'Pan and zoom the map'
    }
}

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
        addMosaicJobListEntry(wf)
    }
    for (const nac in nacData) {
        addFootprint(nac, nacData[nac].status)
    }
}

const addBox = (workflow) => {
    const extent = new boundingExtent([
        [workflow.boundingBox.west, workflow.boundingBox.south],
        [workflow.boundingBox.east, workflow.boundingBox.north],
    ])
    const newFeat = new Feature(fromExtent(extent).transform('EPSG:4326', 'EPSG:3857'))
    newFeat.setId(workflow.metadata.name)
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
    fetch("/api/v1/workflows/default", {
        "headers": {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "content-type": "application/json",
            "pragma": "no-cache"
        },
        "referrer": "/workflows?new=%7B%7D",
        "referrerPolicy": "no-referrer-when-downgrade",
        "body": workflowString,
        "method": "POST",
        "mode": "cors",
        "credentials": "include"
    })
        .then(response => response.json())
        .then(data => console.log(data))
}

const addFootprint = (nacId, status) => {
    fetch(`http://oderest.rsl.wustl.edu/live2/?query=product&results=x&proj=c0&output=JSON&target=moon&pdsid=${nacId}`)
        .then(response => response.json())
        .then(data => {
            for (let footprint in data.ODEResults.Products){
                const footprintWkt = data.ODEResults.Products[footprint].Footprint_C0_geometry
                console.log(footprintWkt)
                const newFeat = new WKT().readFeature(footprintWkt)
                const newFeatGeom = newFeat.getGeometry()
                newFeatGeom.translate(180, 0)
                newFeatGeom.transform('EPSG:4326', 'EPSG:3857')
                newFeat.setId(nacId)
                nacFootprintsSource.addFeature(newFeat)
            }
        })
}

attachToWorkflowEvents(update)