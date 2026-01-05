import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Layout from './components/common/Layout'
import SetupWizard from './pages/SetupWizard'
import Dashboard from './pages/Dashboard'
import Movies from './pages/Movies'
import Recommendations from './pages/Recommendations'
import BadMovies from './pages/BadMovies'
import Issues from './pages/Issues'
import Storage from './pages/Storage'
import Activity from './pages/Activity'
import Settings from './pages/Settings'
import Logs from './pages/Logs'
import { api } from './services/api'

function App() {
  const [setupComplete, setSetupComplete] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    checkSetupStatus()
  }, [])

  const checkSetupStatus = async () => {
    setLoading(true)
    setError(null)
    try {
      // api.get returns the data directly, not wrapped in .data
      const response = await api.get('/api/setup/status')
      setSetupComplete(response.setup_complete || response.is_configured || false)
    } catch (error) {
      console.error('Failed to check setup status:', error)
      setError(error.message || 'Failed to connect to server')
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

  if (error) {
    return (
      <div className="min-h-screen bg-cyber-dark flex items-center justify-center">
        <div className="text-center max-w-md px-4">
          <div className="w-16 h-16 mx-auto mb-4 text-red-500">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-mono text-cyber-accent mb-2">Connection Error</h2>
          <p className="text-gray-400 font-mono text-sm mb-4">{error}</p>
          <button
            onClick={checkSetupStatus}
            className="px-6 py-2 bg-cyber-accent text-cyber-dark font-mono font-bold rounded hover:bg-cyber-accent/80 transition-colors"
          >
            Retry Connection
          </button>
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
        <Route path="/movies" element={<Movies />} />
        <Route path="/recommendations" element={<Recommendations />} />
        <Route path="/bad-movies" element={<BadMovies />} />
        <Route path="/issues" element={<Issues />} />
        <Route path="/storage" element={<Storage />} />
        <Route path="/activity" element={<Activity />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/logs" element={<Logs />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
