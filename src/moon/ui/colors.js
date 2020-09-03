export const statusColors = {
    'select-nacs':     'rgba(207,196,196,0.4)',
    'find-pairs':      'rgba(255, 72,  0,0.4)',
    // 'dl-ingest-nac':   'rgba(255,191,  0,0.4)',
    // 'dl-ingest-left':  'rgba(255,191,  0,0.4)',
    // 'dl-ingest-right': 'rgba(255,191,  0,0.4)',
    'download-nac':    'rgba(129,183, 81,0.4)',
    'img2cub':         'rgba( 85,148,135,0.4)',
    'calibrate':       'rgba(200,  0,255,0.4)',
    'highlighted':     'rgba(255,  0, 21,0.4)'
} 

export const phaseColors = {
    'Pending':   'yellow',
    'Running':   '#0DADEA',
    'Succeeded': '#18BE94'
}

export const createColorKey = ()=>{
    const key = document.getElementById('color-key')
    for (let color in statusColors){
        const newDiv = document.createElement('span')
        newDiv.className = 'color-legend-entry'
        newDiv.setAttribute('style', `background: ${statusColors[color]}`)
        newDiv.innerText = color
        key.appendChild(newDiv)
    }
    for (let color in phaseColors){
        const newDiv = document.createElement('span')
        newDiv.className = 'color-legend-entry'
        newDiv.setAttribute('style', `border: thin ${phaseColors[color]} solid`)
        newDiv.innerText = color
        key.appendChild(newDiv)
    }
}