import 'ol/ol.css'
import {Map, View} from 'ol'
import {Tile as TileLayer, Vector as VectorLayer} from 'ol/layer'
import {XYZ, Vector as VectorSource} from 'ol/source'
import {DragBox} from 'ol/interaction'
import {defaults as defaultControls} from 'ol/control';
import MousePosition from 'ol/control/MousePosition' 
import {createStringXY} from 'ol/coordinate'

let mosaicGoal
const boxDrawLayer = new VectorLayer({source: new VectorSource({wrapX: false})})
const moonBaseMap = new TileLayer({
    source: new XYZ({
        url: 'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/all/{z}/{x}/{y}.png'
    })
})
const dragBox = new DragBox()

const map = new Map({
    target: 'map',
    layers: [
        moonBaseMap, boxDrawLayer
    ],
    view: new View({
        center: [0, 0],
        zoom: 0        
    }),
    interactions: [
        dragBox
    ]
});

const mousePositionControl = new MousePosition({
    coordinateFormat: createStringXY(4),
    projection: 'EPSG:4326'
})
map.addControl(mousePositionControl)

dragBox.on('boxend', (evt)=>{
    mosaicGoal = evt.target.getGeometry().clone().transform('EPSG:3857','EPSG:4326')
    const mosaicExtent = mosaicGoal.getExtent()
    if (confirm(`Begin processing mosaic ${mosaicExtent.map((inp)=>inp.toPrecision(4))} ?`)){
        createMosaic(mosaicExtent)
    }
})

const createMosaic = (mosaicExtent) => {
    // First, download the workflowtemplate for mosaics
    fetch('/api/v1/workflow-templates/default/nac-stereo-wftmpl').then(function (response) {
        return response.json();
    }).then((tmpl)=>{
        tmpl.spec.arguments.parameters = [
            {name: 'west', value: mosaicExtent[0]},
            {name: 'south', value: mosaicExtent[1]},
            {name: 'east', value: mosaicExtent[2]},
            {name: 'north', value: mosaicExtent[3]},
        ]
        submitMosaicWorkflow(tmpl)
    })
}

const submitWorkflowFromTemplate = () => {
    fetch('/api/v1/workflow-templates/default/nac-stereo-wftmpl').then(function (response) {
        return response.json();
    }).then(function (data) {
        const frm = document.createElement('form')
        document.body.appendChild(frm)
        for (let param of data.spec.arguments.parameters){
            const inp = document.createElement('input', )
            const lbl = document.createElement('label')
            lbl.innerText = param.name
            frm.appendChild(lbl)
            frm.appendChild(inp)
            frm.appendChild(document.createElement('p'))
            // create injector into data structure
            inp.onchange = (evt) => {
                param.value = evt.target.value
            }
        }
        const submit = document.createElement('button')
        submit.innerText = 'submit workflow with parameters'
        // change the parameters
        submit.onclick = () => {submitMosaicWorkflow(data)}
        document.body.appendChild(submit)

    });
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

const start_wf = () => {
    fetch('/api/v1/workflows/')
        .then(response => response.json())
        .then(data => console.log(data))
}
document.getElementById('sendreq').click = submitWorkflowFromTemplate