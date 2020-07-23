window.addEventListener('load', (event) => {
    console.log('test')
    document.getElementById('sendreq').onclick = submitWorkflowFromTemplate
})

const submitWorkflow = (evt) => {
    console.log(evt)
}

const submitWorkflowFromTemplate = () => {
    fetch('/api/v1/workflow-templates/default/nac-stereo-wftmpl').then(function (response) {
        return response.json();
    }).then(function (data) {
        const frm = document.createElement('form')
        document.body.appendChild(frm)
        for (param of data.spec.arguments.parameters){
            const inp = document.createElement('input', )
            const lbl = document.createElement('label')
            lbl.innerText = param.name
            frm.appendChild(lbl)
            frm.appendChild(inp)
            frm.appendChild(document.createElement('p'))
        }
        const submit = document.createElement('input')
        submit.type = 'submit'
        submit.onclick = submitWorkflow
        frm.appendChild(submit)

    });
}

const start_wf = () => {
    fetch('http://lmmp-pipeline-ubuntu:32019/api/v1/workflows/')
        .then(response => response.json())
        .then(data => console.log(data))
}
document.getElementById('sendreq').click = start_wf