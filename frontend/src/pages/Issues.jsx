import { useState, useEffect } from 'react'
import { AlertTriangle, RefreshCw, Check, Filter, ChevronDown } from 'lucide-react'
import { api } from '../services/api'

const severityColors = {
  critical: 'cyber-badge-error',
  error: 'cyber-badge-error',
  warning: 'cyber-badge-warning',
  info: 'cyber-badge-info',
}

const severityOrder = ['critical', 'error', 'warning', 'info']

export default function Issues() {
  const [issues, setIssues] = useState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)
  const [filterSeverity, setFilterSeverity] = useState(null)
  const [filterType, setFilterType] = useState(null)
  const [issueTypes, setIssueTypes] = useState([])

  useEffect(() => {
    fetchIssues()
    fetchStats()
    fetchIssueTypes()
  }, [filterSeverity, filterType])

  const fetchIssues = async () => {
    setLoading(true)
    try {
      let endpoint = '/api/issues'
      const params = new URLSearchParams()
      if (filterSeverity) params.append('severity', filterSeverity)
      if (filterType) params.append('issue_type', filterType)
      if (params.toString()) endpoint += `?${params.toString()}`
      
      const response = await api.get(endpoint)
      setIssues(response.data.issues)
    } catch (error) {
      console.error('Failed to fetch issues:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/issues/stats')
      setStats(response.data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const fetchIssueTypes = async () => {
    try {
      const response = await api.get('/api/issues/types')
      setIssueTypes(response.data.types)
    } catch (error) {
      console.error('Failed to fetch issue types:', error)
    }
  }

  const resolveIssue = async (id) => {
    try {
      await api.post('/api/issues/resolve', { issue_id: id })
      setIssues(prev => prev.filter(i => i.id !== id))
      fetchStats()
    } catch (error) {
      console.error('Failed to resolve issue:', error)
    }
  }

  const autoFix = async (id) => {
    try {
      await api.post('/api/issues/auto-fix', { issue_id: id })
      fetchIssues()
      fetchStats()
    } catch (error) {
      console.error('Failed to auto-fix:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <AlertTriangle className="text-cyber-yellow" />
            Issues
          </h1>
          <p className="text-gray-400">Detected problems in your media library</p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-yellow">{stats.total_open}</p>
            <p className="text-sm text-gray-400">Open Issues</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-red">{stats.critical}</p>
            <p className="text-sm text-gray-400">Critical</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-accent">{stats.auto_fixable}</p>
            <p className="text-sm text-gray-400">Auto-Fixable</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-green">{stats.resolved_today}</p>
            <p className="text-sm text-gray-400">Resolved Today</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative">
          <select
            value={filterSeverity || ''}
            onChange={(e) => setFilterSeverity(e.target.value || null)}
            className="cyber-select pr-8"
          >
            <option value="">All Severities</option>
            {severityOrder.map(sev => (
              <option key={sev} value={sev}>{sev.charAt(0).toUpperCase() + sev.slice(1)}</option>
            ))}
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
        <div className="relative">
          <select
            value={filterType || ''}
            onChange={(e) => setFilterType(e.target.value || null)}
            className="cyber-select pr-8"
          >
            <option value="">All Types</option>
            {issueTypes.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
        {(filterSeverity || filterType) && (
          <button 
            onClick={() => { setFilterSeverity(null); setFilterType(null); }}
            className="text-cyber-accent hover:underline text-sm"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Issues List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="animate-spin text-cyber-accent" size={32} />
        </div>
      ) : issues.length > 0 ? (
        <div className="space-y-3">
          {issues.map((issue) => (
            <div key={issue.id} className="cyber-card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`cyber-badge ${severityColors[issue.severity]}`}>
                      {issue.severity.toUpperCase()}
                    </span>
                    <span className="text-xs text-gray-500 font-mono">
                      {issue.issue_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <h3 className="font-semibold">{issue.title}</h3>
                  {issue.description && (
                    <p className="text-sm text-gray-400 mt-1">{issue.description}</p>
                  )}
                  {issue.media_title && (
                    <p className="text-xs text-gray-500 mt-2">
                      {issue.media_type === 'movie' ? '🎬' : '📺'} {issue.media_title}
                    </p>
                  )}
                  {issue.file_path && (
                    <p className="text-xs text-gray-600 mt-1 font-mono truncate">
                      {issue.file_path}
                    </p>
                  )}
                </div>
                <div className="flex gap-2 ml-4">
                  {issue.can_auto_fix && (
                    <button 
                      onClick={() => autoFix(issue.id)}
                      className="cyber-button-primary text-xs py-1 px-3"
                    >
                      Auto-Fix
                    </button>
                  )}
                  <button 
                    onClick={() => resolveIssue(issue.id)}
                    className="cyber-button text-xs py-1 px-3"
                  >
                    <Check size={14} className="mr-1" />
                    Resolve
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <Check size={48} className="text-cyber-green mx-auto mb-4" />
          <p className="text-gray-400">No issues found</p>
          <p className="text-sm text-gray-500">Your library is looking great!</p>
        </div>
      )}
    </div>
  )
}
