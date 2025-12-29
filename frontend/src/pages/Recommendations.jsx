import { useState, useEffect } from 'react'
import { Sparkles, Film, Tv, RefreshCw, ExternalLink, X, Check } from 'lucide-react'
import { api } from '../services/api'

export default function Recommendations() {
  const [activeTab, setActiveTab] = useState('movies')
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    fetchRecommendations()
    fetchStats()
  }, [activeTab])

  const fetchRecommendations = async () => {
    setLoading(true)
    try {
      const endpoint = activeTab === 'movies' ? '/api/recommendations/movies' :
                       activeTab === 'tv' ? '/api/recommendations/tv' : '/api/recommendations/anime'
      const response = await api.get(endpoint)
      // api.get returns data directly, not wrapped in .data
      setRecommendations(response?.recommendations || [])
    } catch (error) {
      console.error('Failed to fetch recommendations:', error)
      setRecommendations([])
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await api.get('/api/recommendations/stats')
      // api.get returns data directly
      setStats(response)
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  const requestItem = async (id) => {
    try {
      await api.post('/api/recommendations/request', { recommendation_id: id })
      setRecommendations(prev => prev.map(r => 
        r.id === id ? { ...r, is_requested: true, requesting: false } : r
      ))
    } catch (error) {
      console.error('Failed to request:', error)
    }
  }

  const ignoreItem = async (id) => {
    try {
      await api.post('/api/recommendations/ignore', { recommendation_id: id })
      setRecommendations(prev => prev.filter(r => r.id !== id))
    } catch (error) {
      console.error('Failed to ignore:', error)
    }
  }

  const regenerate = async () => {
    try {
      await api.post('/api/recommendations/regenerate', { media_type: activeTab === 'movies' ? 'movie' : activeTab })
      fetchRecommendations()
    } catch (error) {
      console.error('Failed to regenerate:', error)
    }
  }

  const tabs = [
    { id: 'movies', label: 'Movies', icon: Film },
    { id: 'tv', label: 'TV Shows', icon: Tv },
    { id: 'anime', label: 'Anime', icon: Sparkles },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="text-cyber-accent" />
            Recommendations
          </h1>
          <p className="text-gray-400">AI-curated suggestions based on your library</p>
        </div>
        <button onClick={regenerate} className="cyber-button">
          <RefreshCw size={18} className="mr-2" />
          Regenerate
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-accent">{stats.pending}</p>
            <p className="text-sm text-gray-400">Pending</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-green">{stats.requested}</p>
            <p className="text-sm text-gray-400">Requested</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-cyber-blue">{stats.added}</p>
            <p className="text-sm text-gray-400">Added</p>
          </div>
          <div className="cyber-card text-center">
            <p className="text-2xl font-bold text-gray-500">{stats.ignored}</p>
            <p className="text-sm text-gray-400">Ignored</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-cyber-border pb-2">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors ${
              activeTab === id 
                ? 'bg-cyber-accent/10 text-cyber-accent border-b-2 border-cyber-accent' 
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Icon size={18} />
            {label}
          </button>
        ))}
      </div>

      {/* Recommendations Grid */}
      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="animate-spin text-cyber-accent" size={32} />
        </div>
      ) : recommendations.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {recommendations.map((rec) => (
            <div key={rec.id} className="cyber-card group">
              {/* Poster placeholder */}
              <div className="aspect-[2/3] bg-cyber-darker rounded-lg mb-3 flex items-center justify-center">
                {rec.poster_url ? (
                  <img src={rec.poster_url} alt={rec.title} className="w-full h-full object-cover rounded-lg" />
                ) : (
                  <Film size={48} className="text-gray-600" />
                )}
              </div>
              
              <h3 className="font-semibold truncate">{rec.title}</h3>
              <p className="text-sm text-gray-400">{rec.year}</p>
              
              {/* Ratings */}
              <div className="flex gap-3 mt-2 text-xs">
                {rec.imdb_rating && (
                  <span className="text-cyber-yellow">IMDb: {rec.imdb_rating}</span>
                )}
                {rec.rotten_tomatoes_rating && (
                  <span className="text-cyber-red">RT: {rec.rotten_tomatoes_rating}%</span>
                )}
              </div>
              
              {/* Reason */}
              {rec.reason && (
                <p className="text-xs text-gray-500 mt-2 line-clamp-2">{rec.reason}</p>
              )}
              
              {/* Actions */}
              <div className="flex gap-2 mt-3">
                {rec.is_requested ? (
                  <span className="cyber-badge-success flex-1 justify-center">
                    <Check size={14} className="mr-1" />
                    Requested
                  </span>
                ) : (
                  <>
                    <button 
                      onClick={() => requestItem(rec.id)}
                      className="cyber-button-primary flex-1 text-sm py-1"
                    >
                      Request
                    </button>
                    <button 
                      onClick={() => ignoreItem(rec.id)}
                      className="cyber-button text-sm py-1 px-2"
                    >
                      <X size={16} />
                    </button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <Sparkles size={48} className="text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No recommendations yet</p>
          <p className="text-sm text-gray-500">Run a scan to generate AI recommendations</p>
        </div>
      )}
    </div>
  )
}
