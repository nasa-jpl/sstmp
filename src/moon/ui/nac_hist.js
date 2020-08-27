import Chart from "chart.js";

export const setupChart = () => {
    Chart.defaults.global.defaultColor="rgba(0,0,0,1)"
    Chart.defaults.global.defaultFontColor = 'white'
    Chart.defaults.global.elements.rectangle.backgroundColor = "white"    
}

setupChart()

export const nacHist = new Chart('hist', {type: 'bar', data: {datsets: [{data: [0]}, {labels: [0]}]}})

export const createCounts = (min, max, num) => {
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



export const nacHistAddData = (evt) => {
    let binLabels = [...Array(evt.data.counts.values.length).keys()].map(n=>n*evt.data.counts.delta)
    binLabels = binLabels.map(n => `> ${n}`)
    nacHist.data = {
        labels: binLabels,
        datasets: [{
            label: 'Pixels with NAC count',
            data: evt.data.counts.values
        }]
    }
}

export const setupHistBins = (evt) => {
    evt.data.counts = createCounts(0, 255, 10)
}