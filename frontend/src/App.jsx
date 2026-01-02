import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect, useCallback } from 'react'
import Layout from './components/common/Layout'
import SetupWizard from './pages/SetupWizard'
import Dashboard from './pages/Dashboard'
import Recommendations from './pages/Recommendations'
import BadMovies from './pages/BadMovies'
import Issues from './pages/Issues'
import Storage from './pages/Storage'
import Activity from './pages/Activity'
import Settings from './pages/Settings'
import Logs from './pages/Logs'
import { api } from './services/api'

// Glitch effect interval (5 minutes in ms)
const GLITCH_INTERVAL = 5 * 60 * 1000

function App() {
  const [setupComplete, setSetupComplete] = useState(null)
  const [loading, setLoading] = useState(true)
  const [glitchEnabled, setGlitchEnabled] = useState(() => {
    // Default to enabled, read from localStorage
    const stored = localStorage.getItem('butlarr_glitch_enabled')
    return stored === null ? true : stored === 'true'
  })
  const [glitchActive, setGlitchActive] = useState(false)

  // Trigger the glitch animation
  const triggerGlitch = useCallback(() => {
    if (!glitchEnabled) return
    setGlitchActive(true)
    // Remove the class after animation completes (700ms)
    setTimeout(() => setGlitchActive(false), 700)
  }, [glitchEnabled])

  // Periodic glitch effect every 5 minutes
  useEffect(() => {
    if (!glitchEnabled || !setupComplete) return

    // Trigger initial glitch after 10 seconds (small delay for dramatic effect)
    const initialTimeout = setTimeout(triggerGlitch, 10000)

    // Then every 5 minutes
    const interval = setInterval(triggerGlitch, GLITCH_INTERVAL)

    return () => {
      clearTimeout(initialTimeout)
      clearInterval(interval)
    }
  }, [glitchEnabled, setupComplete, triggerGlitch])

  // Toggle glitch effect and persist to localStorage
  const toggleGlitch = useCallback((enabled) => {
    setGlitchEnabled(enabled)
    localStorage.setItem('butlarr_glitch_enabled', String(enabled))
    // Enable/disable body class for continuous effects
    if (enabled) {
      document.body.classList.add('glitch-enabled')
    } else {
      document.body.classList.remove('glitch-enabled')
    }
  }, [])

  // Apply glitch-enabled class on mount based on setting
  useEffect(() => {
    if (glitchEnabled) {
      document.body.classList.add('glitch-enabled')
    }
    return () => {
      document.body.classList.remove('glitch-enabled')
    }
  }, [glitchEnabled])

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
    <div className={glitchActive ? 'fullpage-glitch-active' : ''}>
      {/* Glitch lines overlay during effect */}
      {glitchActive && <div className="glitch-lines-overlay" />}

      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/bad-movies" element={<BadMovies />} />
          <Route path="/issues" element={<Issues />} />
          <Route path="/storage" element={<Storage />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/settings" element={
            <Settings
              glitchEnabled={glitchEnabled}
              onGlitchToggle={toggleGlitch}
            />
          } />
          <Route path="/logs" element={<Logs />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </div>
  )
}

export default App
