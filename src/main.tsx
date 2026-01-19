import React from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'

// Global state for React components to communicate with vanilla JS
declare global {
  interface Window {
    diagramCheckboxRefs: {
      topics?: React.RefObject<any>
      queues?: React.RefObject<any>
    }
  }
}

// Initialize global refs and roots
if (typeof window !== 'undefined') {
  (window as any).diagramCheckboxRefs = {}
  (window as any).diagramCheckboxRoots = {}
}

// Export mount function for vanilla JS to use
export function mountDiagramCheckboxes(
  containerId: string,
  type: 'topics' | 'queues',
  items: Array<{ arn: string; name: string }>,
  onSelectionChange: () => void
) {
  const container = document.getElementById(containerId)
  if (!container) {
    console.error(`Container ${containerId} not found`)
    return null
  }

  // Unmount existing root if it exists
  const roots = (window as any).diagramCheckboxRoots || {}
  const rootKey = `${containerId}-${type}`
  if (roots[rootKey]) {
    try {
      roots[rootKey].unmount()
    } catch (e) {
      // Ignore unmount errors
    }
    delete roots[rootKey]
  }

  // Clear container
  container.innerHTML = ''

  // Create new root
  const root = ReactDOM.createRoot(container)
  roots[rootKey] = root
  ;(window as any).diagramCheckboxRoots = roots

  // Import component dynamically
  import('./components/DiagramCheckboxList').then(({ default: DiagramCheckboxList }) => {
    // Create ref if it doesn't exist
    const refs = (window as any).diagramCheckboxRefs || {}
    if (!refs[type]) {
      refs[type] = React.createRef()
      ;(window as any).diagramCheckboxRefs = refs
    }

    root.render(
      React.createElement(DiagramCheckboxList, {
        ref: refs[type],
        items,
        type,
        onSelectionChange
      })
    )
  })

  return root
}

// Export unmount function
export function unmountDiagramCheckboxes(containerId: string) {
  const container = document.getElementById(containerId)
  if (container) {
    container.innerHTML = ''
  }
}

// Make functions available globally for vanilla JS
if (typeof window !== 'undefined') {
  (window as any).mountDiagramCheckboxes = mountDiagramCheckboxes
  ;(window as any).unmountDiagramCheckboxes = unmountDiagramCheckboxes
}

