export class Collapsible extends HTMLElement{
    constructor() {
        super()
        this.addEventListener('click',()=>{
            this.querySelector('details', (evt)=>{
                evt.target.toggleAttribute('open')
            })
        })
    }
    connectedCallback() {
        console.log('collapsible connected')
        const collapsibleTmplClone = document.importNode(
            document.querySelector('#collapsible-tmpl').content, true
        )
        const titleEl = collapsibleTmplClone.querySelector('.title')
        titleEl.innerText = this.getAttribute('title')
        const toggleIndicator = document.createElement('span')
        toggleIndicator.innerText = '◀'
        toggleIndicator.className = 'toggleIndicator'
        titleEl.appendChild(toggleIndicator)
        
        // Move the content from inside the tag down into the right part of the tree 
        collapsibleTmplClone.querySelector('.content').innerHTML = this.innerHTML
        this.innerHTML = ""
        this.appendChild(collapsibleTmplClone)
    }
}