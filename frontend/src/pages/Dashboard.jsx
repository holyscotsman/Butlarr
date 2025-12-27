import { useState, useEffect } from 'react'
import { 
  Film, Tv, AlertTriangle, HardDrive, Trash2, Sparkles,
  Play, Pause, RefreshCw, CheckCircle, Clock
} from 'lucide-react'
import { api, ws } from '../services/api'

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(null)

  useEffect(() => {
    fetchDashboard()
    
    // Connect to scan WebSocket
    ws.connect('scan', (data) => {
      if (data.type === 'scan_progress') {
        setScanProgress(data)
        setScanning(true)
      } else if (data.type === 'scan_complete' || data.type === 'scan_stopped') {
        setScanning(false)
        setScanProgress(null)
        fetchDashboard() // Refresh dashboard
      }
    }, (err) => {
      console.error('WebSocket error:', err)
    })

    return () => ws.disconnect('scan')
  }, [])

  const fetchDashboard = async () => {
    try {
      setError(null)
      const data = await api.get('/api/dashboard')
      setDashboard(data)
      setScanning(data.scan?.is_running || false)
    } catch (err) {
      console.error('Failed to fetch dashboard:', err)
      setError('Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  const startScan = async () => {
    try {
      await api.post('/api/scan/start', {})
      setScanning(true)
    } catch (err) {
      console.error('Failed to start scan:', err)
      setError('Failed to start scan: ' + err.message)
    }
  }

  const stopScan = async () => {
    try {
      await api.post('/api/scan/stop')
      setScanning(false)
      setScanProgress(null)
    } catch (err) {
      console.error('Failed to stop scan:', err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin text-cyber-accent" size={32} />
      </div>
    )
  }

  if (error && !dashboard) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <AlertTriangle className="text-cyber-red mb-4" size={48} />
        <p className="text-cyber-red">{error}</p>
        <button onClick={fetchDashboard} className="cyber-button mt-4">
          <RefreshCw size={16} className="mr-2" />
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-gray-400">Library overview and scan status</p>
        </div>
        <button 
          onClick={scanning ? stopScan : startScan}
          className={scanning ? 'cyber-button-danger' : 'cyber-button-primary'}
        >
          {scanning ? (
            <>
              <Pause size={18} className="mr-2" />
              Stop Scan
            </>
          ) : (
            <>
              <Play size={18} className="mr-2" />
              Start Scan
            </>
          )}
        </button>
      </div>

      {/* Scan Progress */}
      {scanning && scanProgress && (
        <div className="cyber-card border-cyber-accent/30">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <RefreshCw className="animate-spin text-cyber-accent" size={20} />
              <div>
                <h3 className="font-semibold">Scanning Library</h3>
                <p className="text-sm text-gray-400">
                  Phase {scanProgress.phase}/17: {scanProgress.phase_name}
                </p>
              </div>
            </div>
            <span className="text-cyber-accent font-mono">
              {(scanProgress.progress_percent || 0).toFixed(1)}%
            </span>
          </div>
          <div className="cyber-progress">
            <div 
              className="cyber-progress-bar" 
              style={{ width: `${scanProgress.progress_percent || 0}%` }}
            />
          </div>
          {scanProgress.current_item && (
            <p className="text-xs text-gray-500 mt-2 truncate">
              Processing: {scanProgress.current_item}
            </p>
          )}
        </div>
      )}

      {/* Stats Grid - Using explicit classes instead of dynamic */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="cyber-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Movies</p>
              <p className="text-3xl font-bold mt-1">
                {(dashboard?.library?.total_movies || 0).toLocaleString()}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-cyber-accent/10 flex items-center justify-center">
              <Film className="text-cyber-accent" size={24} />
            </div>
          </div>
        </div>

        <div className="cyber-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">TV Shows</p>
              <p className="text-3xl font-bold mt-1">
                {(dashboard?.library?.total_tv_shows || 0).toLocaleString()}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-cyber-pink/10 flex items-center justify-center">
              <Tv className="text-cyber-pink" size={24} />
            </div>
          </div>
        </div>

        <div className="cyber-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Issues</p>
              <p className="text-3xl font-bold mt-1">
                {(dashboard?.library?.issues_count || 0).toLocaleString()}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-cyber-yellow/10 flex items-center justify-center">
              <AlertTriangle className="text-cyber-yellow" size={24} />
            </div>
          </div>
        </div>

        <div className="cyber-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Bad Movies</p>
              <p className="text-3xl font-bold mt-1">
                {(dashboard?.library?.bad_movies_count || 0).toLocaleString()}
              </p>
            </div>
            <div className="w-12 h-12 rounded-lg bg-cyber-red/10 flex items-center justify-center">
              <Trash2 className="text-cyber-red" size={24} />
            </div>
          </div>
        </div>
      </div>

      {/* Two Column Layout */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Service Status */}
        <div className="cyber-card">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <CheckCircle size={18} className="text-cyber-green" />
            Service Status
          </h3>
          <div className="space-y-3">
            {(dashboard?.services || []).map((service) => (
              <div key={service.name} className="flex items-center justify-between">
                <span className="text-gray-300">{service.name}</span>
                <div className="flex items-center gap-2">
                  <div className={service.connected ? 'status-dot status-dot-success' : 'status-dot status-dot-error'} />
                  <span className={service.connected ? 'text-cyber-green' : 'text-cyber-red'}>
                    {service.connected ? 'Connected' : 'Not configured'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* AI Usage */}
        <div className="cyber-card">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Sparkles size={18} className="text-cyber-accent" />
            AI Usage This Month
          </h3>
          {dashboard?.ai?.enabled ? (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Budget Used</span>
                  <span className="text-cyber-accent">
                    ${(dashboard?.ai?.monthly_usage_usd || 0).toFixed(2)} / ${(dashboard?.ai?.monthly_budget_usd || 10).toFixed(2)}
                  </span>
                </div>
                <div className="cyber-progress">
                  <div 
                    className="cyber-progress-bar" 
                    style={{ 
                      width: `${Math.min(100, ((dashboard?.ai?.monthly_usage_usd || 0) / (dashboard?.ai?.monthly_budget_usd || 10)) * 100)}%` 
                    }}
                  />
                </div>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Tokens Used</span>
                <span>{(dashboard?.ai?.tokens_used_this_month || 0).toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">AI is disabled</p>
          )}
        </div>

        {/* Recent Activity */}
        <div className="cyber-card lg:col-span-2">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Clock size={18} className="text-cyber-accent" />
            Recent Activity
          </h3>
          {(dashboard?.recent_activity?.length || 0) > 0 ? (
            <div className="space-y-3">
              {dashboard.recent_activity.map((activity) => (
                <div key={activity.id} className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg">
                  <div className="w-2 h-2 rounded-full bg-cyber-accent flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{activity.title}</p>
                    {activity.description && (
                      <p className="text-xs text-gray-500 truncate">{activity.description}</p>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {new Date(activity.created_at).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No recent activity</p>
          )}
        </div>
      </div>
    </div>
  )
}
