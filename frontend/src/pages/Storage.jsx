import { useState, useEffect } from 'react'
import { HardDrive, RefreshCw, Trash2, AlertTriangle, Check, Copy } from 'lucide-react'
import { api } from '../services/api'

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export default function Storage() {
  const [overview, setOverview] = useState(null)
  const [oversized, setOversized] = useState([])
  const [undersized, setUndersized] = useState([])
  const [duplicates, setDuplicates] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [overviewRes, oversizedRes, undersizedRes, duplicatesRes] = await Promise.all([
        api.get('/api/storage/overview'),
        api.get('/api/storage/oversized'),
        api.get('/api/storage/undersized'),
        api.get('/api/storage/duplicates'),
      ])
      setOverview(overviewRes.data)
      setOversized(oversizedRes.data)
      setUndersized(undersizedRes.data)
      setDuplicates(duplicatesRes.data.groups || [])
    } catch (error) {
      console.error('Failed to fetch storage data:', error)
    } finally {
      setLoading(false)
    }
  }

  const keepVersion = async (movieId, fileId) => {
    try {
      await api.post(`/api/storage/duplicates/${movieId}/keep/${fileId}`)
      fetchData()
    } catch (error) {
      console.error('Failed to keep version:', error)
    }
  }

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'oversized', label: `Oversized (${oversized.length})` },
    { id: 'undersized', label: `Undersized (${undersized.length})` },
    { id: 'duplicates', label: `Duplicates (${duplicates.length})` },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="animate-spin text-cyber-accent" size={32} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <HardDrive className="text-cyber-accent" />
            Storage Optimization
          </h1>
          <p className="text-gray-400">Analyze and optimize your media storage</p>
        </div>
        <button onClick={fetchData} className="cyber-button">
          <RefreshCw size={18} className="mr-2" />
          Refresh
        </button>
      </div>

      {/* Stats */}
      {overview && (
        <div className="grid grid-cols-4 gap-4">
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-accent">{formatBytes(overview.total_size_bytes)}</p>
            <p className="text-sm text-gray-400">Total Size</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-yellow">{overview.oversized_count}</p>
            <p className="text-sm text-gray-400">Oversized Files</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-pink">{overview.duplicates_count}</p>
            <p className="text-sm text-gray-400">Duplicate Files</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-green">{formatBytes(overview.total_reclaimable_bytes)}</p>
            <p className="text-sm text-gray-400">Potential Savings</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-cyber-border pb-2">
        {tabs.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === id 
                ? 'bg-cyber-accent/10 text-cyber-accent border-b-2 border-cyber-accent' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && overview && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Size Breakdown */}
          <div className="cyber-card">
            <h3 className="font-semibold mb-4">Storage Breakdown</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Movies</span>
                  <span>{formatBytes(overview.movies_size_bytes)}</span>
                </div>
                <div className="cyber-progress">
                  <div 
                    className="cyber-progress-bar bg-cyber-accent" 
                    style={{ width: `${(overview.movies_size_bytes / overview.total_size_bytes) * 100}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>TV Shows</span>
                  <span>{formatBytes(overview.tv_size_bytes)}</span>
                </div>
                <div className="cyber-progress">
                  <div 
                    className="cyber-progress-bar bg-cyber-pink" 
                    style={{ width: `${(overview.tv_size_bytes / overview.total_size_bytes) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Reclaimable Space */}
          <div className="cyber-card">
            <h3 className="font-semibold mb-4">Reclaimable Space</h3>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">From oversized files</span>
                <span className="text-cyber-yellow">{formatBytes(overview.oversized_excess_bytes)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">From duplicates</span>
                <span className="text-cyber-pink">{formatBytes(overview.duplicates_waste_bytes)}</span>
              </div>
              <div className="cyber-divider my-3" />
              <div className="flex justify-between font-semibold">
                <span>Total Reclaimable</span>
                <span className="text-cyber-green">{formatBytes(overview.total_reclaimable_bytes)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'oversized' && (
        <div className="space-y-3">
          {oversized.length > 0 ? oversized.map((file) => (
            <div key={file.id} className="cyber-card flex items-center justify-between">
              <div>
                <h4 className="font-medium">{file.title} ({file.year})</h4>
                <p className="text-sm text-gray-500">{file.resolution}</p>
              </div>
              <div className="text-right">
                <p className="text-cyber-yellow font-mono">{formatBytes(file.file_size_bytes)}</p>
                <p className="text-xs text-gray-500">
                  Expected: {formatBytes(file.expected_max_bytes)} | Excess: {formatBytes(file.excess_bytes)}
                </p>
              </div>
            </div>
          )) : (
            <div className="text-center py-16">
              <Check size={48} className="text-cyber-green mx-auto mb-4" />
              <p className="text-gray-400">No oversized files found</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'undersized' && (
        <div className="space-y-3">
          {undersized.length > 0 ? undersized.map((file) => (
            <div key={file.id} className="cyber-card flex items-center justify-between">
              <div>
                <h4 className="font-medium">{file.title} ({file.year})</h4>
                <p className="text-sm text-gray-500">{file.resolution}</p>
              </div>
              <div className="text-right">
                <p className="text-cyber-red font-mono">{formatBytes(file.file_size_bytes)}</p>
                <p className="text-xs text-gray-500">
                  Expected min: {formatBytes(file.expected_min_bytes)}
                </p>
              </div>
            </div>
          )) : (
            <div className="text-center py-16">
              <Check size={48} className="text-cyber-green mx-auto mb-4" />
              <p className="text-gray-400">No undersized files found</p>
            </div>
          )}
        </div>
      )}

      {activeTab === 'duplicates' && (
        <div className="space-y-4">
          {duplicates.length > 0 ? duplicates.map((group) => (
            <div key={group.movie_id} className="cyber-card">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h4 className="font-medium">{group.title} ({group.year})</h4>
                  <p className="text-sm text-gray-500">
                    {group.files.length} versions · Save {formatBytes(group.potential_savings_bytes)}
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                {group.files.map((file) => (
                  <div 
                    key={file.id} 
                    className={`flex items-center justify-between p-3 rounded-lg ${
                      file.is_recommended ? 'bg-cyber-green/10 border border-cyber-green/30' : 'bg-cyber-darker'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {file.is_recommended && (
                        <span className="cyber-badge-success">Recommended</span>
                      )}
                      <div>
                        <p className="text-sm font-mono">{file.resolution} · {file.video_codec}</p>
                        <p className="text-xs text-gray-500">{formatBytes(file.file_size_bytes)}</p>
                      </div>
                    </div>
                    {!file.is_recommended && (
                      <button
                        onClick={() => keepVersion(group.movie_id, file.id)}
                        className="cyber-button text-xs py-1"
                      >
                        Keep This
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )) : (
            <div className="text-center py-16">
              <Check size={48} className="text-cyber-green mx-auto mb-4" />
              <p className="text-gray-400">No duplicate files found</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
