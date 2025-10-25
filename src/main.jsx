import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './App.css' // <-- 必须是这样！没有 "from"，没有变量名
import APP from './APP.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <APP />
  </StrictMode>,
)