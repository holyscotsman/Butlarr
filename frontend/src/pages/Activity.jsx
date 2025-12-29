import { useState, useEffect } from 'react'
import { Activity as ActivityIcon, RefreshCw, Trash2, ChevronDown } from 'lucide-react'
import { api } from '../services/api'
import { format, formatDistanceToNow } from 'date-fns'

const actionIcons = {
  scan_started: '🔄',
  scan_completed: '✅',
  scan_failed: '❌',
  movie_deleted: '🗑️',
  movie_ignored: '👁️',
  recommendation_requested: '📥',
  recommendation_ignored: '🚫',
  file_renamed: '✏️',
  file_moved: '📁',
  duplicate_removed: '🧹',
  issue_resolved: '🔧',
  settings_changed: '⚙️',
  ai_query: '🤖',
}

export default function Activity() {
  const [activities, setActivities] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionTypes, setActionTypes] = useState([])
  const [filterType, setFilterType] = useState(null)
  const [filterDays, setFilterDays] = useState(30)

  useEffect(() => {
    fetchActivity()
    fetchActionTypes()
  }, [filterType, filterDays])

  const fetchActivity = async () => {
    setLoading(true)
    try {
      let endpoint = `/api/activity?days=${filterDays}&limit=100`
      if (filterType) endpoint += `&action_type=${filterType}`

      const response = await api.get(endpoint)
      // api.get returns data directly, not wrapped in .data
      setActivities(response?.activities || response || [])
    } catch (error) {
      console.error('Failed to fetch activity:', error)
      setActivities([])
    } finally {
      setLoading(false)
    }
  }

  const fetchActionTypes = async () => {
    try {
      const response = await api.get('/api/activity/types')
      // api.get returns data directly, not wrapped in .data
      setActionTypes(response?.types || response || [])
    } catch (error) {
      console.error('Failed to fetch action types:', error)
      setActionTypes([])
    }
  }

  const clearOldActivity = async () => {
    if (!confirm(`Clear activity older than ${filterDays} days?`)) return
    
    try {
      await api.delete(`/api/activity/clear?before_days=${filterDays}`)
      fetchActivity()
    } catch (error) {
      console.error('Failed to clear activity:', error)
    }
  }

  const groupByDate = (items) => {
    const groups = {}
    items.forEach(item => {
      const date = format(new Date(item.created_at), 'yyyy-MM-dd')
      if (!groups[date]) groups[date] = []
      groups[date].push(item)
    })
    return groups
  }

  const groupedActivities = groupByDate(activities)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <ActivityIcon className="text-cyber-accent" />
            Activity Log
          </h1>
          <p className="text-gray-400">Track all actions and changes in your library</p>
        </div>
        <button onClick={clearOldActivity} className="cyber-button-danger">
          <Trash2 size={18} className="mr-2" />
          Clear Old
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative">
          <select
            value={filterType || ''}
            onChange={(e) => setFilterType(e.target.value || null)}
            className="cyber-select pr-8"
          >
            <option value="">All Actions</option>
            {actionTypes.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
        <div className="relative">
          <select
            value={filterDays}
            onChange={(e) => setFilterDays(Number(e.target.value))}
            className="cyber-select pr-8"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
          <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
        </div>
      </div>

      {/* Activity List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="animate-spin text-cyber-accent" size={32} />
        </div>
      ) : activities.length > 0 ? (
        <div className="space-y-6">
          {Object.entries(groupedActivities).map(([date, items]) => (
            <div key={date}>
              <h3 className="text-sm font-medium text-gray-500 mb-3 sticky top-0 bg-cyber-dark py-2">
                {format(new Date(date), 'EEEE, MMMM d, yyyy')}
              </h3>
              <div className="space-y-2">
                {items.map((activity) => (
                  <div 
                    key={activity.id} 
                    className="cyber-card flex items-start gap-4"
                  >
                    <div className="text-2xl">
                      {actionIcons[activity.action_type] || '📋'}
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{activity.title}</p>
                      {activity.description && (
                        <p className="text-sm text-gray-400 mt-1">{activity.description}</p>
                      )}
                    </div>
                    <div className="text-right text-sm">
                      <p className="text-gray-500">
                        {format(new Date(activity.created_at), 'h:mm a')}
                      </p>
                      <p className="text-xs text-gray-600">
                        {formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <ActivityIcon size={48} className="text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No activity found</p>
          <p className="text-sm text-gray-500">Activity will appear here after scans and actions</p>
        </div>
      )}
    </div>
  )
}
