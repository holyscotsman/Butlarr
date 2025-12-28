import { useState, useEffect, useCallback } from 'react'
import { Trash2, RefreshCw, AlertTriangle, Check, X, HardDrive, ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../services/api'

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const PAGE_SIZE = 25

export default function BadMovies() {
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [stats, setStats] = useState(null)
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [deleting, setDeleting] = useState(false)
  const [deletingId, setDeletingId] = useState(null) // Track individual delete operations
  const [ignoringId, setIgnoringId] = useState(null) // Track individual ignore operations

  // Pagination state
  const [page, setPage] = useState(0)
  const [totalItems, setTotalItems] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  const totalPages = Math.ceil(totalItems / PAGE_SIZE)

  const fetchMovies = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.get('/api/bad-movies', {
        params: {
          limit: PAGE_SIZE,
          offset: page * PAGE_SIZE,
          sort_by: 'score'
        }
      })
      setMovies(response.movies || [])
      setTotalItems(response.total || 0)
      setHasMore(response.has_more || false)
    } catch (err) {
      console.error('Failed to fetch bad movies:', err)
      setError('Failed to load bad movies. Please try again.')
      setMovies([])
    } finally {
      setLoading(false)
    }
  }, [page])

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/bad-movies/stats')
      setStats(response)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  useEffect(() => {
    fetchMovies()
  }, [fetchMovies])

  useEffect(() => {
    fetchStats()
  }, [])

  const deleteMovie = async (id) => {
    if (!confirm('Are you sure you want to delete this movie? This cannot be undone.')) return

    // Store movie for potential rollback
    const movieIndex = movies.findIndex(m => m.id === id)
    const movieBackup = movies[movieIndex]

    setDeletingId(id)

    // Optimistic update
    setMovies(prev => prev.filter(m => m.id !== id))

    try {
      await api.post('/api/bad-movies/delete', { suggestion_id: id, confirm: true })
      fetchStats() // Update stats after successful deletion
    } catch (err) {
      console.error('Failed to delete:', err)
      // Rollback on error
      setMovies(prev => {
        const newMovies = [...prev]
        newMovies.splice(movieIndex, 0, movieBackup)
        return newMovies
      })
      setError(`Failed to delete: ${err.message || 'Unknown error'}`)
    } finally {
      setDeletingId(null)
    }
  }

  const ignoreMovie = async (id) => {
    // Store movie for potential rollback
    const movieIndex = movies.findIndex(m => m.id === id)
    const movieBackup = movies[movieIndex]

    setIgnoringId(id)

    // Optimistic update
    setMovies(prev => prev.filter(m => m.id !== id))

    try {
      await api.post('/api/bad-movies/ignore', { suggestion_id: id })
      fetchStats()
    } catch (err) {
      console.error('Failed to ignore:', err)
      // Rollback on error
      setMovies(prev => {
        const newMovies = [...prev]
        newMovies.splice(movieIndex, 0, movieBackup)
        return newMovies
      })
      setError(`Failed to ignore: ${err.message || 'Unknown error'}`)
    } finally {
      setIgnoringId(null)
    }
  }

  const bulkDelete = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`Delete ${selectedIds.size} movies? This cannot be undone.`)) return

    // Store movies for potential rollback
    const selectedMovies = movies.filter(m => selectedIds.has(m.id))

    setDeleting(true)

    // Optimistic update
    setMovies(prev => prev.filter(m => !selectedIds.has(m.id)))
    const previousSelectedIds = new Set(selectedIds)
    setSelectedIds(new Set())

    try {
      const result = await api.post('/api/bad-movies/bulk-delete', {
        suggestion_ids: Array.from(previousSelectedIds),
        confirm: true
      })

      // If some failed, add them back
      if (result.failed && result.failed.length > 0) {
        const failedIds = new Set(result.failed.map(f => f.id))
        const failedMovies = selectedMovies.filter(m => failedIds.has(m.id))
        if (failedMovies.length > 0) {
          setMovies(prev => [...prev, ...failedMovies])
          setError(`${result.failed.length} movies failed to delete`)
        }
      }

      fetchStats()
    } catch (err) {
      console.error('Failed to bulk delete:', err)
      // Rollback on error
      setMovies(prev => [...prev, ...selectedMovies])
      setSelectedIds(previousSelectedIds)
      setError(`Bulk delete failed: ${err.message || 'Unknown error'}`)
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

  const goToPage = (newPage) => {
    if (newPage >= 0 && newPage < totalPages) {
      setPage(newPage)
      setSelectedIds(new Set()) // Clear selection when changing pages
    }
  }

  const dismissError = () => setError(null)

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
        <div className="flex items-center gap-3">
          <button
            onClick={fetchMovies}
            disabled={loading}
            className="cyber-button"
            title="Refresh"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
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
      </div>

      {/* Error Alert */}
      {error && (
        <div className="bg-cyber-red/10 border border-cyber-red/30 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <X className="text-cyber-red flex-shrink-0" size={20} />
            <p className="text-cyber-red">{error}</p>
          </div>
          <button onClick={dismissError} className="text-cyber-red hover:text-white">
            <X size={18} />
          </button>
        </div>
      )}

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
        <>
          <div className="cyber-panel overflow-hidden">
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-4 p-4 border-b border-cyber-border bg-cyber-darker text-sm font-medium text-gray-400">
              <div className="col-span-1">
                <input
                  type="checkbox"
                  checked={selectedIds.size === movies.length && movies.length > 0}
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
                } ${(deletingId === movie.id || ignoringId === movie.id) ? 'opacity-50' : ''}`}
              >
                <div className="col-span-1">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(movie.id)}
                    onChange={() => toggleSelect(movie.id)}
                    disabled={deletingId === movie.id || ignoringId === movie.id}
                    className="rounded border-cyber-border bg-cyber-darker"
                  />
                </div>
                <div className="col-span-4">
                  <p className="font-medium">{movie.title}</p>
                  <p className="text-sm text-gray-500">{movie.year}</p>
                  {movie.reason && (
                    <p className="text-xs text-gray-600 mt-1 truncate" title={movie.reason}>
                      {movie.reason}
                    </p>
                  )}
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
                    disabled={ignoringId === movie.id || deletingId === movie.id}
                    className="cyber-button text-xs py-1 px-2"
                    title="Keep (Ignore)"
                  >
                    {ignoringId === movie.id ? (
                      <RefreshCw size={14} className="animate-spin" />
                    ) : (
                      <Check size={14} />
                    )}
                  </button>
                  <button
                    onClick={() => deleteMovie(movie.id)}
                    disabled={deletingId === movie.id || ignoringId === movie.id}
                    className="cyber-button-danger text-xs py-1 px-2"
                    title="Delete"
                  >
                    {deletingId === movie.id ? (
                      <RefreshCw size={14} className="animate-spin" />
                    ) : (
                      <Trash2 size={14} />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4">
              <p className="text-sm text-gray-400">
                Showing {page * PAGE_SIZE + 1}-{Math.min((page + 1) * PAGE_SIZE, totalItems)} of {totalItems}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => goToPage(page - 1)}
                  disabled={page === 0}
                  className="cyber-button py-1 px-2 disabled:opacity-50"
                >
                  <ChevronLeft size={18} />
                </button>
                <span className="text-sm text-gray-400 px-2">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => goToPage(page + 1)}
                  disabled={!hasMore && page === totalPages - 1}
                  className="cyber-button py-1 px-2 disabled:opacity-50"
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>
          )}
        </>
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
