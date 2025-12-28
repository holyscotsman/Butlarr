import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/common/Layout'
import SetupWizard from './pages/SetupWizard'
import Dashboard from './pages/Dashboard'
import Recommendations from './pages/Recommendations'
import BadMovies from './pages/BadMovies'
import Issues from './pages/Issues'
import Storage from './pages/Storage'
import Activity from './pages/Activity'
import Settings from './pages/Settings'
import { api } from './services/api'

function App() {
  const [setupComplete, setSetupComplete] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkSetupStatus()
  }, [])

  const checkSetupStatus = async () => {
    try {
      // api.get returns the data directly, not wrapped in .data
      const response = await api.get('/api/setup/status')
      setSetupComplete(response.setup_complete || response.is_configured || false)
    } catch (error) {
      console.error('Failed to check setup status:', error)
      setSetupComplete(false)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-cyber-dark flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-cyber-accent border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-cyber-accent font-mono">Initializing Butlarr...</p>
        </div>
      </div>
    )
  }

  if (!setupComplete) {
    return <SetupWizard onComplete={() => setSetupComplete(true)} />
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/bad-movies" element={<BadMovies />} />
        <Route path="/issues" element={<Issues />} />
        <Route path="/storage" element={<Storage />} />
        <Route path="/activity" element={<Activity />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
