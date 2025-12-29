/**
 * Logs Page Component
 *
 * Displays application logs with filtering, search, and download capabilities.
 * Useful for debugging and monitoring application behavior.
 *
 * Features:
 * - Real-time log viewing
 * - Filter by log level
 * - Search functionality
 * - Download full logs
 * - Auto-refresh option
 */

import { useState, useEffect, useRef } from 'react'
import {
  FileText,
  RefreshCw,
  Download,
  Search,
  Filter,
  Trash2,
  AlertCircle,
  AlertTriangle,
  Info,
  Bug,
  ChevronDown,
  Play,
  Pause
} from 'lucide-react'
import { api } from '../services/api'

// Log level icons and colors
const LOG_LEVELS = {
  debug: { icon: Bug, color: 'text-gray-400', bg: 'bg-gray-500/10' },
  info: { icon: Info, color: 'text-cyber-accent', bg: 'bg-cyber-accent/10' },
  warning: { icon: AlertTriangle, color: 'text-cyber-yellow', bg: 'bg-cyber-yellow/10' },
  error: { icon: AlertCircle, color: 'text-cyber-red', bg: 'bg-cyber-red/10' },
}

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterLevel, setFilterLevel] = useState('all')
  const [lineCount, setLineCount] = useState(200)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [refreshInterval, setRefreshInterval] = useState(5)
  const logsEndRef = useRef(null)

  // Fetch logs
  const fetchLogs = async () => {
    try {
      setError(null)
      const data = await api.get(`/api/system/logs?lines=${lineCount}`)

      // Parse log lines into structured format
      const parsedLogs = (data.logs || []).map((line, index) => {
        const parsed = parseLogLine(line)
        return { ...parsed, id: index, raw: line }
      })

      setLogs(parsedLogs)
    } catch (err) {
      console.error('Failed to fetch logs:', err)
      setError('Failed to load logs: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  // Parse a log line into structured data
  const parseLogLine = (line) => {
    // Try to parse JSON structured logs
    try {
      const json = JSON.parse(line)
      return {
        timestamp: json.timestamp || new Date().toISOString(),
        level: (json.level || 'info').toLowerCase(),
        message: json.event || json.message || line,
        logger: json.logger || '',
        details: json,
      }
    } catch {
      // Fall back to text parsing
      const levelMatch = line.match(/\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b/i)
      const level = levelMatch ? levelMatch[1].toLowerCase() : 'info'

      const timestampMatch = line.match(/\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/)
      const timestamp = timestampMatch ? timestampMatch[0] : ''

      return {
        timestamp,
        level: level === 'critical' ? 'error' : level,
        message: line,
        logger: '',
        details: null,
      }
    }
  }

  // Auto-refresh effect
  useEffect(() => {
    fetchLogs()

    if (autoRefresh) {
      const interval = setInterval(fetchLogs, refreshInterval * 1000)
      return () => clearInterval(interval)
    }
  }, [lineCount, autoRefresh, refreshInterval])

  // Download logs
  const downloadLogs = async () => {
    try {
      const response = await fetch('/api/system/logs/download')
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `butlarr-logs-${new Date().toISOString().split('T')[0]}.log`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Failed to download logs:', err)
      alert('Failed to download logs: ' + err.message)
    }
  }

  // Filter logs
  const filteredLogs = logs.filter(log => {
    // Level filter
    if (filterLevel !== 'all' && log.level !== filterLevel) {
      return false
    }

    // Search filter
    if (searchTerm) {
      const search = searchTerm.toLowerCase()
      return (
        log.message.toLowerCase().includes(search) ||
        log.logger.toLowerCase().includes(search) ||
        log.raw.toLowerCase().includes(search)
      )
    }

    return true
  })

  // Scroll to bottom
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

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
            <FileText className="text-cyber-accent" />
            Application Logs
          </h1>
          <p className="text-gray-400">View and download application logs for debugging</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`cyber-button ${autoRefresh ? 'bg-cyber-green/20 border-cyber-green text-cyber-green' : ''}`}
            title={autoRefresh ? 'Stop auto-refresh' : 'Start auto-refresh'}
          >
            {autoRefresh ? <Pause size={18} /> : <Play size={18} />}
            {autoRefresh ? 'Stop' : 'Auto'}
          </button>
          <button onClick={fetchLogs} className="cyber-button">
            <RefreshCw size={18} />
            Refresh
          </button>
          <button onClick={downloadLogs} className="cyber-button-primary">
            <Download size={18} />
            Download
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4 items-center">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search logs..."
            className="cyber-input pl-10 w-full"
          />
        </div>

        {/* Level filter */}
        <div className="relative">
          <select
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="cyber-select pr-8"
          >
            <option value="all">All Levels</option>
            <option value="debug">Debug</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>

        {/* Line count */}
        <div className="relative">
          <select
            value={lineCount}
            onChange={(e) => setLineCount(Number(e.target.value))}
            className="cyber-select pr-8"
          >
            <option value={100}>Last 100 lines</option>
            <option value={200}>Last 200 lines</option>
            <option value={500}>Last 500 lines</option>
            <option value={1000}>Last 1000 lines</option>
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>

        {/* Results count */}
        <span className="text-sm text-gray-400">
          {filteredLogs.length} of {logs.length} entries
        </span>
      </div>

      {/* Error display */}
      {error && (
        <div className="p-4 bg-cyber-red/10 border border-cyber-red/30 rounded-lg flex items-center gap-3">
          <AlertCircle className="text-cyber-red" size={20} />
          <span className="text-cyber-red">{error}</span>
        </div>
      )}

      {/* Logs display */}
      <div className="cyber-card p-0 overflow-hidden">
        <div className="max-h-[600px] overflow-y-auto font-mono text-sm">
          {filteredLogs.length > 0 ? (
            <table className="w-full">
              <thead className="sticky top-0 bg-cyber-darker border-b border-cyber-border">
                <tr>
                  <th className="px-4 py-2 text-left text-gray-400 w-[180px]">Timestamp</th>
                  <th className="px-4 py-2 text-left text-gray-400 w-[80px]">Level</th>
                  <th className="px-4 py-2 text-left text-gray-400">Message</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map((log) => {
                  const levelConfig = LOG_LEVELS[log.level] || LOG_LEVELS.info
                  const Icon = levelConfig.icon

                  return (
                    <tr key={log.id} className="border-b border-cyber-border/30 hover:bg-cyber-darker/50">
                      <td className="px-4 py-2 text-gray-500 whitespace-nowrap">
                        {log.timestamp}
                      </td>
                      <td className="px-4 py-2">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${levelConfig.color} ${levelConfig.bg}`}>
                          <Icon size={12} />
                          {log.level.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-300 break-all">
                        {log.message}
                        {log.logger && (
                          <span className="text-gray-600 ml-2">[{log.logger}]</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-16 text-gray-500">
              <FileText size={48} className="mx-auto mb-4 opacity-50" />
              <p>No logs found</p>
              <p className="text-sm">Logs will appear here as the application runs</p>
            </div>
          )}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Debug mode info */}
      <div className="p-4 bg-cyber-darker rounded-lg">
        <h3 className="font-medium text-cyber-accent mb-2 flex items-center gap-2">
          <Bug size={18} />
          Debug Information
        </h3>
        <p className="text-sm text-gray-400 mb-2">
          To enable verbose debug logging, set the environment variable:
        </p>
        <code className="block p-3 bg-cyber-dark rounded text-sm text-cyber-green">
          DEBUG=true
        </code>
        <p className="text-sm text-gray-500 mt-2">
          Or in docker-compose.yml, add <code className="text-cyber-accent">- DEBUG=true</code> to the environment section.
        </p>
      </div>
    </div>
  )
}
