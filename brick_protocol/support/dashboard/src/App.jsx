import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Projects from './pages/Projects.jsx'
import ProjectDetail from './pages/ProjectDetail.jsx'
import Building from './pages/Building.jsx'
import Brick from './pages/Brick.jsx'
import Agent from './pages/Agent.jsx'
import LinkPage from './pages/Link.jsx'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Projects />} />
        <Route path="/project/:id" element={<ProjectDetail />} />
        <Route path="/building" element={<Building />} />
        <Route path="/building/:id" element={<Building />} />
        <Route path="/brick" element={<Brick />} />
        <Route path="/agent" element={<Agent />} />
        <Route path="/link" element={<LinkPage />} />
      </Routes>
    </Layout>
  )
}
