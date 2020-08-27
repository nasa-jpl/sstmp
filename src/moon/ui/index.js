import 'ol/ol.css'
import {Map, View} from 'ol'
import {Tile as TileLayer, Vector as VectorLayer, Image as ImageLayer} from 'ol/layer'
import {XYZ, Vector as VectorSource, Raster as RasterSource} from 'ol/source'
import {DragBox} from 'ol/interaction'
import {fromExtent} from "ol/geom/Polygon";
import MousePosition from 'ol/control/MousePosition' 
import {createStringXY} from 'ol/coordinate'
import {Feature} from 'ol'
import {boundingExtent} from 'ol/extent'
import {Fill, Stroke, Style, Text} from 'ol/style';
import WKT from "ol/format/WKT";
import Chart from 'chart.js'


let mosaicGoal

// workflowData is an object to cache all of the app state. Its format is like:
// {workflowName: {metadata: ..., boundingBox: {east: 1, south: , west: , north: }, status: {...}}}
const workflowData = {}
const nacData = {}
let highlightedMosaicBB = null

const boxDrawSource = new VectorSource({wrapX: false})
const nacFootprintsSource = new VectorSource({wrapX: false})

Chart.defaults.global.defaultColor="rgba(0,0,0,1)"

const createStyle = (fillColor, strokeColor) => new Style({
    text: new Text({
        text: '',
        font: `18px sans-serif`,
        placement: 'point',
        overflow: true,
        fill: new Fill({color: 'blue'})
    }),
    stroke: new Stroke({color: strokeColor, width: 1}),
    fill: new Fill({color: fillColor})
}) 

const mosaicBBstyleWlabel = (feature, resolution) => {
    let featStyle
    const mosaicBBstyles = {
        mosaicBB: createStyle('rgba(255,255,255,0.4)', 'blue'),
        mosaicBBhighlight: createStyle('rgb(255,255,255)', 'blue')
    }
    if (feature.id_ === highlightedMosaicBB){
        featStyle = mosaicBBstyles['mosaicBBhighlight']  
    } else {
        featStyle = mosaicBBstyles['mosaicBB']
    }
    featStyle.getText().setText(feature.id_)
    return featStyle 
}
const boxDrawLayer = new VectorLayer({
    source: boxDrawSource,
    style: mosaicBBstyleWlabel
})

const nacFootprintsStyle = (feature, resolution) => {
    const nacFootprintStyles = {
        Pending: createStyle('rgba(255,255,255,0.4)','grey'),
        PendingHighlight: createStyle('rgba(255,255,255,1)','grey'),
        Running: createStyle('rgba(255,255,255,0.4)','yellow'),
        RunningHighlight: createStyle('rgba(255,255,255,1)','yellow'),
        Succeeded: createStyle('rgba(255,255,255,0.4)','green'),
        SucceededHighlight: createStyle('rgba(255,255,255,1)','green')
    }
    const featData = nacData[feature.id_]
    return nacFootprintStyles[featData.phase]
}

const nacFootprintsLayer = new VectorLayer({
    source: nacFootprintsSource,
    style: nacFootprintsStyle
})

const hillshade = new TileLayer({
    source: new XYZ({
        url: 'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/1/{z}/{x}/{y}.png',
    }),
    name: 'hillshade'
})

const nomenclature = new TileLayer({
    source: new XYZ({
        url: 'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/3/{z}/{x}/{y}.png'
    }),
    name: 'nomenclature'
})

const nacAvailTilesXyzSource = new XYZ({
    url: 'http://acdesk.jpl.nasa.gov:81/files/globalNACcover/NAC_availability.tif/{z}/{x}/{-y}.png',
    crossOrigin: ''
})

const op = (pixels, data)=>{
    let sourcePixel = pixels[0]
    sourcePixel[0] = sourcePixel[0] * 4
    summarize(sourcePixel[0], data.counts)
    return sourcePixel
}

const nacAvailTilesRasterSource = new RasterSource({
    sources: [nacAvailTilesXyzSource],
    operation: op,
    lib: {summarize: summarize}
})

function createCounts(min, max, num) {
    var values = new Array(num);
    for (var i = 0; i < num; ++i) {
        values[i] = 0;
    }
    return {
        min: min,
        max: max,
        values: values,
        delta: (max - min) / num,
    };
}

/**
 * Add incoming data into the histogram bins
 * @param value
 * @param counts
 */
function summarize(value, counts) {
    var min = counts.min;
    var max = counts.max;
    var num = counts.values.length;
    if (value < min) {
        // do nothing
    } else if (value >= max) {
        counts.values[num - 1] += 1;
    } else {
        // find what bin it goes in
        var index = Math.floor((value - min) / counts.delta);
        counts.values[index] += 1;
    }
}

// Before running the operations, set up histogram bins
nacAvailTilesRasterSource.on('beforeoperations', (evt)=>{
    evt.data.counts = createCounts(0, 255, 10)
})
Chart.defaults.global.defaultFontColor = 'white'
Chart.defaults.global.elements.rectangle.backgroundColor = "white"
const chart = new Chart('hist', {type: 'bar', data: {datsets: [{data: [0]}, {labels: [0]}]}})
window.mychart = chart
nacAvailTilesRasterSource.on('afteroperations', (evt) => {
    let binLabels = [...Array(evt.data.counts.values.length).keys()].map(n=>n*evt.data.counts.delta)
    binLabels = binLabels.map(n => `> ${n}`) 
    chart.data = {
            labels: binLabels,
            datasets: [{
                label: 'Pixels with NAC count',
                data: evt.data.counts.values
            }]
        }
})

const nac_avail_tiles = new ImageLayer({
    source: nacAvailTilesRasterSource,
    name: 'nac_avail',
    visible: false
})


// map setup
const moonmap = new Map({
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
        chart.update(0)
    }
})

// Expose the map globally to allow savvy users to mess with it
window.moonmap = moonmap

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

const highlight = (workflowName)=>{
    highlightedMosaicBB = workflowName
    boxDrawSource.changed()
    if (highlightedMosaicBB){
        document.getElementsByClassName(highlightedMosaicBB)[0].classList.add('highlighted')
    } else {
        let highlightedEls = document.getElementsByClassName('highlighted')
        if (highlightedEls.length > 0){
            highlightedEls[0].classList.remove('highlighted')
        }
    }
}

/**
 * Adds a mosaic workflow to the "Mosaic jobs" list
 * @param workflow
 */
const addMosaicJobListEntry = (workflow) => {
    const mosaicsList = document.getElementById('workflow-list-content')
    const wfdetails = document.createElement('details')
    const wfsummary = document.createElement('summary')
    wfdetails.appendChild(wfsummary)
    wfsummary.className = workflow.metadata.name
    wfsummary.onmouseover = (evt) => {highlight(evt.target.className)}
    wfsummary.onmouseleave = (evt) => {highlight(null)}
    const wfLink = document.createElement('a')
    wfLink.className = workflow.metadata.name
    wfLink.href = `/workflows/${workflow.metadata.namespace}/${workflow.metadata.name}`
    wfLink.target = '_blank'
    wfLink.innerText = `${workflow.metadata.name}, ${workflow.status.phase}`
    wfsummary.appendChild(wfLink)
    
    // Accordion
    wfsummary.onclick = (evt) => {
        console.log('accordion')
        evt.target.toggleAttribute('expanded')
    }

    // add nacs under each mosaic job
    const nacsul = document.createElement('ul')
    nacsul.className = workflow.metadata.name
    wfdetails.appendChild(nacsul)
    for (const nac in nacData){
        if (nacData[nac].workflowName === workflow.metadata.name){
            const nacli = document.createElement('li')
            // status and phase are kind of backwards thanks to Argo :-p
            nacli.innerText = `${nac}, ${nacData[nac].status}, ${nacData[nac].phase}`
            nacsul.appendChild(nacli)
        }
    }
    
    mosaicsList.appendChild(wfdetails)
}

const attachToWorkflowEvents = () => {
    const eventSource = new EventSource('/api/v1/workflow-events/default')
    // receive the message and cache the important parts into workflowData
    eventSource.onmessage = (evt) => {
        const data = JSON.parse(evt.data)
        const wfName = data.result.object.metadata.name
        if (wfName.startsWith('nac')){
            if (data.result.type == "DELETED") {
                delete workflowData[wfName]
            } else {
                const wfNodes = data.result.object.status.nodes
                const topNode = wfNodes[wfName]
    
                // Extract useful mosaic-level data from the response
                workflowData[wfName] = {
                    metadata: data.result.object.metadata,
                    boundingBox: arrayToObject(topNode.inputs.parameters),
                    status: data.result.object.status
                }
    
                // Collect useful image-level data from the response
                const nodes = data.result.object.status.nodes
                // The template names representing statuses where the first parameter is the nacid
                const statusTemplateNames = ['download-nac', 'img2cub', 'calibrate']
                for (let node in nodes) {
                    // Check that the current node is one of the ones we're interested in
                    if (statusTemplateNames.includes(nodes[node].templateName)) {
                        let nacid = nodes[node].inputs.parameters[0].value
                        // If there's no status yet, or this node is newer than the one we used to set the status
                        if (!nacData.hasOwnProperty(nacid) ||
                            (Date.parse(nodes[node].startedAt) > Date.parse(nacData[nacid].nodeStartedAt))) {
                            nacData[nacid] = {
                                status: nodes[node].templateName,
                                phase: nodes[node].phase,
                                nodeStartedAt: nodes[node].startedAt,
                                workflowName: wfName
                            }
                        }
                    }
                }
                update()
            }
        }
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
        addMosaicJobListEntry(wf)
    }
    for (const nac in nacData) {
        addFootprint(nac, nacData[nac].status)
    }
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

attachToWorkflowEvents()