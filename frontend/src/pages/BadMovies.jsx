import { useState, useEffect } from 'react'
import { Trash2, RefreshCw, AlertTriangle, Check, X, HardDrive } from 'lucide-react'
import { api } from '../services/api'

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export default function BadMovies() {
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    fetchMovies()
    fetchStats()
  }, [])

  const fetchMovies = async () => {
    setLoading(true)
    try {
      const response = await api.get('/api/bad-movies')
      setMovies(response.data.movies)
    } catch (error) {
      console.error('Failed to fetch bad movies:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/bad-movies/stats')
      setStats(response.data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const deleteMovie = async (id) => {
    if (!confirm('Are you sure you want to delete this movie? This cannot be undone.')) return
    
    try {
      await api.post('/api/bad-movies/delete', { suggestion_id: id, confirm: true })
      setMovies(prev => prev.filter(m => m.id !== id))
      fetchStats()
    } catch (error) {
      console.error('Failed to delete:', error)
    }
  }

  const ignoreMovie = async (id) => {
    try {
      await api.post('/api/bad-movies/ignore', { suggestion_id: id })
      setMovies(prev => prev.filter(m => m.id !== id))
      fetchStats()
    } catch (error) {
      console.error('Failed to ignore:', error)
    }
  }

  const bulkDelete = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`Delete ${selectedIds.size} movies? This cannot be undone.`)) return
    
    setDeleting(true)
    try {
      await api.post('/api/bad-movies/bulk-delete', { 
        suggestion_ids: Array.from(selectedIds),
        confirm: true 
      })
      setMovies(prev => prev.filter(m => !selectedIds.has(m.id)))
      setSelectedIds(new Set())
      fetchStats()
    } catch (error) {
      console.error('Failed to bulk delete:', error)
    } finally {
      setDeleting(false)
    }
  }

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const selectAll = () => {
    if (selectedIds.size === movies.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(movies.map(m => m.id)))
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Trash2 className="text-cyber-red" />
            Bad Movies
          </h1>
          <p className="text-gray-400">AI-identified movies that could be removed</p>
        </div>
        {selectedIds.size > 0 && (
          <button 
            onClick={bulkDelete}
            disabled={deleting}
            className="cyber-button-danger"
          >
            {deleting ? (
              <RefreshCw size={18} className="animate-spin mr-2" />
            ) : (
              <Trash2 size={18} className="mr-2" />
            )}
            Delete {selectedIds.size} Selected
          </button>
        )}
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-red">{stats.pending}</p>
            <p className="text-sm text-gray-400">Pending Review</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-gray-500">{stats.ignored}</p>
            <p className="text-sm text-gray-400">Ignored</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-green">{stats.deleted}</p>
            <p className="text-sm text-gray-400">Deleted</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-accent">{formatBytes(stats.potential_savings_bytes)}</p>
            <p className="text-sm text-gray-400">Potential Savings</p>
          </div>
        </div>
      )}

      {/* Warning */}
      <div className="bg-cyber-yellow/10 border border-cyber-yellow/30 rounded-lg p-4 flex items-start gap-3">
        <AlertTriangle className="text-cyber-yellow flex-shrink-0 mt-0.5" size={20} />
        <div>
          <p className="font-medium text-cyber-yellow">Review Before Deleting</p>
          <p className="text-sm text-gray-400">
            These movies have been flagged by AI based on low ratings. Movies requested via Overseerr 
            and cult classics are protected. Always review before deleting.
          </p>
        </div>
      </div>

      {/* Movie List */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="animate-spin text-cyber-accent" size={32} />
        </div>
      ) : movies.length > 0 ? (
        <div className="cyber-panel overflow-hidden">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-4 p-4 border-b border-cyber-border bg-cyber-darker text-sm font-medium text-gray-400">
            <div className="col-span-1">
              <input 
                type="checkbox" 
                checked={selectedIds.size === movies.length}
                onChange={selectAll}
                className="rounded border-cyber-border bg-cyber-darker"
              />
            </div>
            <div className="col-span-4">Movie</div>
            <div className="col-span-1 text-center">Score</div>
            <div className="col-span-1 text-center">IMDb</div>
            <div className="col-span-1 text-center">RT</div>
            <div className="col-span-2">Size</div>
            <div className="col-span-2 text-right">Actions</div>
          </div>

          {/* Movie Rows */}
          {movies.map((movie) => (
            <div 
              key={movie.id} 
              className={`grid grid-cols-12 gap-4 p-4 border-b border-cyber-border items-center hover:bg-cyber-darker/50 transition-colors ${
                selectedIds.has(movie.id) ? 'bg-cyber-red/5' : ''
              }`}
            >
              <div className="col-span-1">
                <input 
                  type="checkbox" 
                  checked={selectedIds.has(movie.id)}
                  onChange={() => toggleSelect(movie.id)}
                  className="rounded border-cyber-border bg-cyber-darker"
                />
              </div>
              <div className="col-span-4">
                <p className="font-medium">{movie.title}</p>
                <p className="text-sm text-gray-500">{movie.year}</p>
              </div>
              <div className="col-span-1 text-center">
                <span className={`cyber-badge ${
                  movie.bad_score >= 8 ? 'cyber-badge-error' : 
                  movie.bad_score >= 6 ? 'cyber-badge-warning' : 'cyber-badge-info'
                }`}>
                  {movie.bad_score?.toFixed(1)}
                </span>
              </div>
              <div className="col-span-1 text-center text-cyber-yellow">
                {movie.imdb_rating || '-'}
              </div>
              <div className="col-span-1 text-center text-cyber-red">
                {movie.rotten_tomatoes_rating ? `${movie.rotten_tomatoes_rating}%` : '-'}
              </div>
              <div className="col-span-2 flex items-center gap-2">
                <HardDrive size={14} className="text-gray-500" />
                <span className="text-sm">{formatBytes(movie.file_size_bytes)}</span>
              </div>
              <div className="col-span-2 flex justify-end gap-2">
                <button 
                  onClick={() => ignoreMovie(movie.id)}
                  className="cyber-button text-xs py-1 px-2"
                  title="Keep (Ignore)"
                >
                  <Check size={14} />
                </button>
                <button 
                  onClick={() => deleteMovie(movie.id)}
                  className="cyber-button-danger text-xs py-1 px-2"
                  title="Delete"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <Check size={48} className="text-cyber-green mx-auto mb-4" />
          <p className="text-gray-400">No bad movies found</p>
          <p className="text-sm text-gray-500">Your library is in great shape!</p>
        </div>
      )}
    </div>
  )
}
