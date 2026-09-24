import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import DiagramApp from './DiagramViewer.tsx'

// ?diagram=<name> selects DIAGRAM mode: a standalone presentation viewer with
// its own chrome, fully separate from the build viewer (see DiagramViewer.tsx).
const diagramName = new URLSearchParams(window.location.search).get('diagram')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {diagramName ? <DiagramApp name={diagramName} /> : <App />}
  </StrictMode>,
)
