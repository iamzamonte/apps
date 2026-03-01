import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { PortfolioNew } from './pages/PortfolioNew'
import { PortfolioDetail } from './pages/PortfolioDetail'
import { PortfolioEdit } from './pages/PortfolioEdit'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/portfolio/new" element={<PortfolioNew />} />
          <Route path="/portfolio/:id" element={<PortfolioDetail />} />
          <Route path="/portfolio/:id/edit" element={<PortfolioEdit />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App
