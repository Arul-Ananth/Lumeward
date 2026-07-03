import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Remove provider credentials saved by frontend versions that exposed settings.
try {
  localStorage.removeItem('userArgs_apiKey')
  localStorage.removeItem('userArgs_serperKey')
} catch {
  // Storage can be unavailable under restrictive browser privacy policies.
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
