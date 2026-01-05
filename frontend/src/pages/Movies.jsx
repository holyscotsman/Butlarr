import { useState, useEffect, useCallback } from 'react'
import {
  Film, Search, Trash2, RefreshCw, ChevronLeft, ChevronRight,
  Filter, X, Check, AlertTriangle, Copy, ExternalLink, HardDrive
} from 'lucide-react'
import { api } from '../services/api'

export default function Movies() {
  const [movies, setMovies] = useState([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [stats, setStats] = useState(null)

  // Pagination
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)

  // Filters
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('title')
  const [sortOrder, setSortOrder] = useState('asc')
  const [filterResolution, setFilterResolution] = useState('')
  const [filterHdr, setFilterHdr] = useState(null)
  const [showFilters, setShowFilters] = useState(false)

  // Delete modal
  const [deleteModal, setDeleteModal] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const fetchMovies = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })

      if (search) params.append('search', search)
      if (filterResolution) params.append('resolution', filterResolution)
      if (filterHdr !== null) params.append('is_hdr', filterHdr.toString())

      const data = await api.get(`/api/movies?${params}`)
      setMovies(data.movies || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (error) {
      console.error('Failed to fetch movies:', error)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, sortBy, sortOrder, filterResolution, filterHdr])

  const fetchStats = async () => {
    try {
      const data = await api.get('/api/movies/stats')
      setStats(data)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  useEffect(() => {
    fetchMovies()
  }, [fetchMovies])

  useEffect(() => {
    fetchStats()
  }, [])

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      setPage(1)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const handleSync = async () => {
    setSyncing(true)
    try {
      await api.post('/api/movies/sync')
      await fetchMovies()
      await fetchStats()
    } catch (error) {
      console.error('Sync failed:', error)
    } finally {
      setSyncing(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteModal) return
    setDeleting(true)
    try {
      await api.delete(`/api/movies/${deleteModal.id}`)
      setDeleteModal(null)
      await fetchMovies()
      await fetchStats()
    } catch (error) {
      console.error('Delete failed:', error)
      alert(`Failed to delete: ${error.message}`)
    } finally {
      setDeleting(false)
    }
  }

  const formatSize = (bytes) => {
    if (!bytes) return '-'
    const gb = bytes / (1024 * 1024 * 1024)
    return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / (1024 * 1024)).toFixed(0)} MB`
  }

  const formatDuration = (minutes) => {
    if (!minutes) return '-'
    const h = Math.floor(minutes / 60)
    const m = minutes % 60
    return h > 0 ? `${h}h ${m}m` : `${m}m`
  }

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('asc')
    }
    setPage(1)
  }

  const SortHeader = ({ column, label }) => (
    <th
      className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider cursor-pointer hover:text-cyber-accent transition-colors"
      onClick={() => handleSort(column)}
    >
      <div className="flex items-center gap-1">
        {label}
        {sortBy === column && (
          <span className="text-cyber-accent">{sortOrder === 'asc' ? '↑' : '↓'}</span>
        )}
      </div>
    </th>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3">
            <Film className="text-cyber-accent" />
            Movie Library
          </h1>
          <p className="text-gray-400 mt-1">
            {total.toLocaleString()} movies • {stats ? formatSize(stats.total_size_bytes) : '-'} total
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="cyber-button"
          >
            <RefreshCw size={18} className={syncing ? 'animate-spin' : ''} />
            {syncing ? 'Syncing...' : 'Sync from Plex'}
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-accent">{stats.total_movies}</p>
            <p className="text-xs text-gray-400">Total Movies</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold">{formatSize(stats.total_size_bytes)}</p>
            <p className="text-xs text-gray-400">Total Size</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-green">{stats.hdr_count}</p>
            <p className="text-xs text-gray-400">HDR Movies</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-yellow">{stats.duplicate_movies}</p>
            <p className="text-xs text-gray-400">With Duplicates</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold">{stats.average_rating || '-'}</p>
            <p className="text-xs text-gray-400">Avg IMDb Rating</p>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search movies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="cyber-input pl-10 w-full"
          />
        </div>

        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`cyber-button ${showFilters ? 'bg-cyber-accent/20' : ''}`}
        >
          <Filter size={18} />
          Filters
        </button>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="cyber-card flex flex-wrap gap-4 items-center">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Resolution</label>
            <select
              value={filterResolution}
              onChange={(e) => { setFilterResolution(e.target.value); setPage(1); }}
              className="cyber-input text-sm"
            >
              <option value="">All</option>
              <option value="4k">4K</option>
              <option value="1080p">1080p</option>
              <option value="720p">720p</option>
              <option value="480p">480p</option>
            </select>
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">HDR</label>
            <select
              value={filterHdr === null ? '' : filterHdr.toString()}
              onChange={(e) => {
                setFilterHdr(e.target.value === '' ? null : e.target.value === 'true');
                setPage(1);
              }}
              className="cyber-input text-sm"
            >
              <option value="">All</option>
              <option value="true">HDR Only</option>
              <option value="false">SDR Only</option>
            </select>
          </div>

          <button
            onClick={() => {
              setFilterResolution('');
              setFilterHdr(null);
              setSearch('');
              setPage(1);
            }}
            className="cyber-button text-sm mt-5"
          >
            <X size={14} />
            Clear Filters
          </button>
        </div>
      )}

      {/* Movies Table */}
      <div className="cyber-card overflow-hidden p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-cyber-darker border-b border-cyber-border">
              <tr>
                <SortHeader column="title" label="Title" />
                <SortHeader column="year" label="Year" />
                <SortHeader column="rating" label="IMDb" />
                <SortHeader column="resolution" label="Quality" />
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Codec</th>
                <SortHeader column="size" label="Size" />
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Duration</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-400 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cyber-border">
              {loading ? (
                <tr>
                  <td colSpan="9" className="px-4 py-8 text-center text-gray-400">
                    <RefreshCw className="animate-spin mx-auto mb-2" size={24} />
                    Loading movies...
                  </td>
                </tr>
              ) : movies.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-4 py-8 text-center text-gray-400">
                    No movies found. Try adjusting your filters or sync from Plex.
                  </td>
                </tr>
              ) : (
                movies.map((movie) => (
                  <tr key={movie.id} className="hover:bg-cyber-darker/50 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{movie.title}</span>
                        {movie.is_hdr && (
                          <span className="px-1.5 py-0.5 text-xs bg-cyber-green/20 text-cyber-green rounded">
                            {movie.hdr_type || 'HDR'}
                          </span>
                        )}
                      </div>
                      {movie.genres && movie.genres.length > 0 && (
                        <p className="text-xs text-gray-500 mt-0.5">
                          {movie.genres.slice(0, 3).join(' • ')}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-400">{movie.year || '-'}</td>
                    <td className="px-4 py-3">
                      {movie.imdb_rating ? (
                        <span className={`font-medium ${
                          movie.imdb_rating >= 7 ? 'text-cyber-green' :
                          movie.imdb_rating >= 5 ? 'text-cyber-yellow' : 'text-cyber-red'
                        }`}>
                          {movie.imdb_rating.toFixed(1)}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs rounded ${
                        movie.resolution === '4k' ? 'bg-purple-500/20 text-purple-400' :
                        movie.resolution === '1080p' ? 'bg-blue-500/20 text-blue-400' :
                        movie.resolution === '720p' ? 'bg-green-500/20 text-green-400' :
                        'bg-gray-500/20 text-gray-400'
                      }`}>
                        {movie.resolution || 'Unknown'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {movie.video_codec || '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-400">{formatSize(movie.file_size_bytes)}</td>
                    <td className="px-4 py-3 text-gray-400">{formatDuration(movie.duration_minutes)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {movie.has_duplicates && (
                          <span className="px-1.5 py-0.5 text-xs bg-cyber-yellow/20 text-cyber-yellow rounded flex items-center gap-1">
                            <Copy size={10} />
                            {movie.duplicate_count}
                          </span>
                        )}
                        {movie.is_bad_movie && (
                          <span className="px-1.5 py-0.5 text-xs bg-cyber-red/20 text-cyber-red rounded">
                            Bad
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {movie.imdb_id && (
                          <a
                            href={`https://www.imdb.com/title/${movie.imdb_id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1.5 text-gray-400 hover:text-cyber-accent transition-colors"
                            title="View on IMDb"
                          >
                            <ExternalLink size={16} />
                          </a>
                        )}
                        <button
                          onClick={() => setDeleteModal(movie)}
                          className="p-1.5 text-gray-400 hover:text-cyber-red transition-colors"
                          title="Delete movie"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-cyber-border bg-cyber-darker">
            <p className="text-sm text-gray-400">
              Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, total)} of {total}
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="cyber-button text-sm disabled:opacity-50"
              >
                <ChevronLeft size={16} />
              </button>
              <span className="text-sm text-gray-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="cyber-button text-sm disabled:opacity-50"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {deleteModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="cyber-card max-w-md w-full">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-cyber-red/20 rounded-lg">
                <AlertTriangle className="text-cyber-red" size={24} />
              </div>
              <h3 className="text-lg font-bold">Delete Movie</h3>
            </div>

            <p className="text-gray-400 mb-4">
              Are you sure you want to delete <strong className="text-white">{deleteModal.title}</strong>
              {deleteModal.year && ` (${deleteModal.year})`}?
            </p>

            <p className="text-sm text-gray-500 mb-6">
              This will remove the movie from Radarr and delete all associated files.
              This action cannot be undone.
            </p>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteModal(null)}
                className="cyber-button"
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                disabled={deleting}
                className="cyber-button bg-cyber-red/20 border-cyber-red/50 text-cyber-red hover:bg-cyber-red/30"
              >
                {deleting ? (
                  <>
                    <RefreshCw size={16} className="animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 size={16} />
                    Delete Movie
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
