import {Tile as TileLayer, Vector as VectorLayer, Image as ImageLayer} from 'ol/layer'
import {XYZ, Vector as VectorSource, Raster as RasterSource} from 'ol/source'
import {Fill, Stroke, Style, Text} from "ol/style";
import {nacHistAddData, setupHistBins} from "./nac_hist";
import "./nac_hist"
import {nacData} from "./rxdata";


export const boxDrawSource = new VectorSource({wrapX: false})
export const nacFootprintsSource = new VectorSource({wrapX: false})

// highlightedMosaicBB is a string containing the id of the currently highlighted mosaic
let highlightedMosaicBB = null

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
export const mosaicFootprints = new VectorLayer({
    source: boxDrawSource,
    style: mosaicBBstyleWlabel,
    name: 'mosaicFootprints'
})


export const highlight = (workflowName)=>{
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
export const addMosaicJobListEntry = (workflow) => {
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

export const nacFootprintsLayer = new VectorLayer({
    source: nacFootprintsSource,
    style: nacFootprintsStyle,
    name: 'nacFootprints'
})

export const hillshade = new TileLayer({
    source: new XYZ({
        url: 'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/1/{z}/{x}/{y}.png',
    }),
    name: 'hillshade'
})

export const nomenclature = new TileLayer({
    source: new XYZ({
        url: 'https://cartocdn-gusc.global.ssl.fastly.net/opmbuilder/api/v1/map/named/opm-moon-basemap-v0-1/3/{z}/{x}/{y}.png'
    }),
    name: 'nomenclature'
})

const nacAvailTilesXyzSource = new XYZ({
    url: 'https://eyeritac.sirv.com/NACcoverageCounts/{z}/{x}/{-y}.png',
    crossOrigin: ''
})

/**
 * Add incoming data into the histogram bins
 * should be in nac_hist.js, but openlayers worker creation was failing due to module issue
 * @param value
 * @param counts
 */
const addToHistData = (value, counts) => {
    const min = counts.min;
    const max = counts.max;
    const num = counts.values.length;
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

const nacAvailTilesRasterSource = new RasterSource({
    sources: [nacAvailTilesXyzSource],
    operation: (pixels, data) => {
        let sourcePixel = pixels[0]
        sourcePixel[0] = sourcePixel[0] * 4
        addToHistData(sourcePixel[0], data.counts)
        return sourcePixel
    },
    lib: {'addToHistData': addToHistData}
})

nacAvailTilesRasterSource.on('beforeoperations', setupHistBins)
nacAvailTilesRasterSource.on('afteroperations', nacHistAddData)

export const nac_avail_tiles = new ImageLayer({
    source: nacAvailTilesRasterSource,
    name: 'nac_avail',
    visible: false
})