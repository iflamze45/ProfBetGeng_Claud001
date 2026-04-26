import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import SovereignTerminal from './SovereignTerminal.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <SovereignTerminal />
  </StrictMode>,
)
