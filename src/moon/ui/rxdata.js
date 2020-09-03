

// workflowData is an object to cache all of the app state representing workflows. Its format is like:
// {workflowName: {metadata: ..., boundingBox: {east: 1, south: , west: , north: }, status: {...}}}
import {update} from "./index";
import {arrayToObject} from "./util";
import {nacStatusColors, mosStatusColors} from "./colors";
 

export const workflowData = {}

// nacData is an object to cache all of the app state representing imagery.
export const nacData = {}

export const attachToWorkflowEvents = (updateCallback) => {
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

                // Collect useful image-level data from the response
                const nodes = data.result.object.status.nodes
                // The template names representing statuses where the first parameter is the nacid
                for (let node in nodes) {
                    // If the current node represents a whole mosaic TODO doesn't work properly for stereo
                    if ((nodes[node].type === 'TaskGroup')
                        || ['find-pairs','select-nacs','equalizer','noseam','cub2tif']
                            .includes(nodes[node].templateName)) {
                        if (!workflowData.hasOwnProperty(wfName) ||
                            (Date.parse(nodes[node].startedAt) > Date.parse(workflowData[wfName].nodeStartedAt))){
                            workflowData[wfName] = {
                                metadata: data.result.object.metadata,
                                status: nodes[node].templateName,
                                phase: nodes[node].phase,
                                nodeStartedAt: nodes[node].startedAt,
                                boundingBox: arrayToObject(topNode.inputs.parameters)
                            }
                        }
                    }
                    // If the current node represents a nac image
                    else if (Object.keys(nacStatusColors).includes(nodes[node].templateName)) {
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
            }
            updateCallback()
        }
    }
}