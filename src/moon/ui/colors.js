// Todo: probably makes sense to combine nac and mos status colors into one object

export const nacStatusColors = {
    'download-nac':    'rgba(129,183, 81,0.4)',
    'img2cub':         'rgba( 85,148,135,0.4)',
    'calibrate':       'rgba(200,  0,255,0.4)',
    'cam2map':         'rgba(255,  0,161,0.4)',
    'highlighted':     'rgba(255,  0, 21,  1)'
} 

export const mosStatusColors = {
    'select-nacs':     'rgba(207,196,196,0.4)',
    'find-pairs':      'rgba(255,200,  0,0.4)',     // stereo-only
    'dl-ingest-nac':   'rgba(255, 72,  0,0.4)',
    'mosrange':        'rgba(129,183, 81,0.4)',
    'equalizer':       'rgba( 85,148,135,0.4)',
    'cam2map':         'rgba(200,  0,255,0.4)',
    'noseam':          'rgba(255,  0,161,0.4)',
    'cub2tif':         'rgba(255,200,  0,0.4)',
    
    // UI
    'highlighted':     'rgba(255,  0, 21, 1)',    
}

export const phaseColors = {
    'Pending':   'yellow',
    'Running':   '#0DADEA',
    'Succeeded': '#18BE94'
}

export const createColorKey = ()=>{
    for (let color in phaseColors){
        const newDiv = document.createElement('span')
        newDiv.className = 'color-legend-entry'
        newDiv.setAttribute('style', `border: thin ${phaseColors[color]} solid`)
        newDiv.innerText = color
        document.getElementById('phase-color-key').appendChild(newDiv)
    }
    for (let color in nacStatusColors){
        const newDiv = document.createElement('span')
        newDiv.className = 'color-legend-entry'
        newDiv.setAttribute('style', `background: ${nacStatusColors[color]}`)
        newDiv.innerText = color
        document.getElementById('nac-color-key').appendChild(newDiv)
    }
    for (let color in mosStatusColors){
        const newDiv = document.createElement('span')
        newDiv.className = 'color-legend-entry'
        newDiv.setAttribute('style', `background: ${mosStatusColors[color]}`)
        newDiv.innerText = color
        document.getElementById('mos-color-key').appendChild(newDiv)
    }
}