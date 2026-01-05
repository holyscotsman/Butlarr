import { useState, useEffect } from 'react'
import {
  Server, Film, Tv, Bell, BarChart, FileText, Sparkles,
  ChevronRight, ChevronLeft, Check, X, RefreshCw, ArrowRight,
  Download, Loader2, Database, AlertTriangle
} from 'lucide-react'
import { api } from '../services/api'

const steps = [
  { id: 'plex', title: 'Connect Plex', icon: Server },
  { id: 'services', title: 'Services', icon: Database },
  { id: 'ai', title: 'AI Setup', icon: Sparkles },
]

export default function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(0)
  const [version, setVersion] = useState(null)

  // Plex state
  const [plex, setPlex] = useState({ url: '', token: '' })
  const [plexConnected, setPlexConnected] = useState(false)
  const [plexTesting, setPlexTesting] = useState(false)
  const [plexResult, setPlexResult] = useState(null)

  // Library fetch state
  const [libraryLoading, setLibraryLoading] = useState(false)
  const [libraryData, setLibraryData] = useState(null)

  // Services state (all on one page)
  const [services, setServices] = useState({
    radarr: { url: '', api_key: '', connected: false, testing: false, result: null },
    sonarr: { url: '', api_key: '', connected: false, testing: false, result: null },
    overseerr: { url: '', api_key: '', connected: false, testing: false, result: null },
    tautulli: { url: '', api_key: '', connected: false, testing: false, result: null },
    filebot: { url: '', username: '', password: '', connected: false, testing: false, result: null },
  })

  // AI state
  const [ai, setAi] = useState({
    anthropic_api_key: '',
    openai_api_key: '',
  })
  const [aiSaved, setAiSaved] = useState(false)

  // Local LLM state
  const [localLlm, setLocalLlm] = useState({
    available: false,
    downloading: false,
    downloadProgress: 0,
    installed: false,
    modelName: 'Llama 3.2 3B',
    modelSize: '2.0 GB',
  })

  // Fetch version on mount
  useEffect(() => {
    api.get('/api/system/info')
      .then(data => data && setVersion(data.version))
      .catch(() => {})

    // Check local LLM status
    checkLocalLlmStatus()
  }, [])

  const checkLocalLlmStatus = async () => {
    try {
      const status = await api.get('/api/ai/local/status')
      setLocalLlm(prev => ({
        ...prev,
        available: true,
        installed: status.installed || false,
        modelName: status.model_name || 'Llama 3.2 3B',
        modelSize: status.model_size || '2.0 GB',
      }))
    } catch {
      // Local LLM not available
    }
  }

  // Test and configure Plex
  const testPlex = async () => {
    setPlexTesting(true)
    setPlexResult(null)

    try {
      const result = await api.post('/api/setup/test/plex', plex)

      if (result.success) {
        await api.post('/api/setup/configure/plex', plex)
        setPlexConnected(true)
        setPlexResult({ success: true, message: result.message })

        // Immediately start fetching library
        fetchLibrary()
      } else {
        setPlexResult({ success: false, message: result.message })
      }
    } catch (error) {
      setPlexResult({ success: false, message: error.message })
    } finally {
      setPlexTesting(false)
    }
  }

  // Fetch library data from Plex
  const fetchLibrary = async () => {
    setLibraryLoading(true)
    try {
      const [movies, shows] = await Promise.all([
        api.get('/api/scan/movies/quick'),
        api.get('/api/scan/shows/quick'),
      ])

      setLibraryData({
        movies: movies.items || movies || [],
        shows: shows.items || shows || [],
        movieCount: movies.count || (movies.items || movies || []).length,
        showCount: shows.count || (shows.items || shows || []).length,
        duplicates: movies.duplicates || 0,
      })
    } catch (error) {
      console.error('Failed to fetch library:', error)
      // Non-critical - continue anyway
      setLibraryData({ movies: [], shows: [], movieCount: 0, showCount: 0, duplicates: 0 })
    } finally {
      setLibraryLoading(false)
    }
  }

  // Test a service
  const testService = async (serviceName) => {
    const service = services[serviceName]

    setServices(prev => ({
      ...prev,
      [serviceName]: { ...prev[serviceName], testing: true, result: null }
    }))

    try {
      const testData = serviceName === 'filebot'
        ? { url: service.url, username: service.username, password: service.password }
        : { url: service.url, api_key: service.api_key }

      const result = await api.post(`/api/setup/test/${serviceName}`, testData)

      if (result.success) {
        await api.post(`/api/setup/configure/${serviceName}`, testData)
        setServices(prev => ({
          ...prev,
          [serviceName]: { ...prev[serviceName], connected: true, result: { success: true, message: result.message } }
        }))
      } else {
        setServices(prev => ({
          ...prev,
          [serviceName]: { ...prev[serviceName], result: { success: false, message: result.message } }
        }))
      }
    } catch (error) {
      setServices(prev => ({
        ...prev,
        [serviceName]: { ...prev[serviceName], result: { success: false, message: error.message } }
      }))
    } finally {
      setServices(prev => ({
        ...prev,
        [serviceName]: { ...prev[serviceName], testing: false }
      }))
    }
  }

  // Update service field
  const updateService = (serviceName, field, value) => {
    setServices(prev => ({
      ...prev,
      [serviceName]: { ...prev[serviceName], [field]: value }
    }))
  }

  // Save AI configuration
  const saveAiConfig = async () => {
    try {
      await api.post('/api/setup/configure/ai', ai)
      setAiSaved(true)
    } catch (error) {
      console.error('Failed to save AI config:', error)
    }
  }

  // Download local LLM
  const downloadLocalLlm = async () => {
    setLocalLlm(prev => ({ ...prev, downloading: true, downloadProgress: 0 }))

    try {
      // Start download
      await api.post('/api/ai/local/download')

      // Poll for progress
      const pollProgress = setInterval(async () => {
        try {
          const status = await api.get('/api/ai/local/status')
          setLocalLlm(prev => ({
            ...prev,
            downloadProgress: status.download_progress || 0,
            installed: status.installed || false,
          }))

          if (status.installed) {
            clearInterval(pollProgress)
            setLocalLlm(prev => ({ ...prev, downloading: false }))
          }
        } catch {
          // Continue polling
        }
      }, 2000)

      // Timeout after 10 minutes
      setTimeout(() => {
        clearInterval(pollProgress)
        setLocalLlm(prev => ({ ...prev, downloading: false }))
      }, 600000)
    } catch (error) {
      console.error('Failed to download LLM:', error)
      setLocalLlm(prev => ({ ...prev, downloading: false }))
    }
  }

  // Complete setup
  const completeSetup = async () => {
    try {
      await api.post('/api/setup/complete', { confirm: true })

      // Trigger initial AI analysis if AI is configured
      if (ai.anthropic_api_key || ai.openai_api_key || localLlm.installed) {
        try {
          await api.post('/api/scan/analyze', { full_analysis: true })
        } catch {
          // Non-critical
        }
      }

      onComplete()
    } catch (error) {
      console.error('Failed to complete setup:', error)
    }
  }

  const nextStep = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const renderStep = () => {
    switch (steps[currentStep].id) {
      case 'plex':
        return (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <div className="w-20 h-20 bg-cyber-accent rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-cyber-lg pulse-glow">
                <span className="text-cyber-dark font-bold text-4xl">B</span>
              </div>
              <h2 className="text-3xl font-bold mb-2 heading-glow">Welcome to Butlarr</h2>
              {version && <p className="text-sm text-cyber-accent/60 font-mono mb-2">v{version}</p>}
              <p className="text-gray-400">Connect your Plex server to get started</p>
            </div>

            <div className="cyber-card space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Plex Server URL</label>
                <input
                  type="text"
                  placeholder="http://192.168.1.100:32400"
                  value={plex.url}
                  onChange={(e) => setPlex(p => ({ ...p, url: e.target.value }))}
                  className="cyber-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">X-Plex-Token</label>
                <input
                  type="password"
                  placeholder="Your Plex authentication token"
                  value={plex.token}
                  onChange={(e) => setPlex(p => ({ ...p, token: e.target.value }))}
                  className="cyber-input"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Find your token in any Plex library item's XML URL or browser dev tools
                </p>
              </div>

              {plexResult && (
                <div className={`p-3 rounded-lg ${plexResult.success ? 'bg-cyber-green/10 border border-cyber-green/30' : 'bg-cyber-red/10 border border-cyber-red/30'}`}>
                  <div className="flex items-center gap-2">
                    {plexResult.success ? <Check className="text-cyber-green" size={18} /> : <X className="text-cyber-red" size={18} />}
                    <span className={plexResult.success ? 'text-cyber-green' : 'text-cyber-red'}>{plexResult.message}</span>
                  </div>
                </div>
              )}

              <button
                onClick={testPlex}
                disabled={plexTesting || !plex.url || !plex.token}
                className="cyber-button-primary w-full"
              >
                {plexTesting ? (
                  <>
                    <RefreshCw size={18} className="mr-2 animate-spin" />
                    Connecting...
                  </>
                ) : plexConnected ? (
                  <>
                    <Check size={18} className="mr-2" />
                    Connected - Test Again
                  </>
                ) : (
                  <>
                    <Server size={18} className="mr-2" />
                    Connect to Plex
                  </>
                )}
              </button>
            </div>

            {/* Library Status */}
            {plexConnected && (
              <div className="cyber-card">
                <h3 className="font-semibold mb-3 flex items-center gap-2">
                  <Database size={18} className="text-cyber-accent" />
                  Library Status
                </h3>

                {libraryLoading ? (
                  <div className="flex items-center gap-3 text-gray-400">
                    <Loader2 size={20} className="animate-spin" />
                    <span>Fetching library data...</span>
                  </div>
                ) : libraryData ? (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="text-center p-3 bg-cyber-darker rounded-lg">
                      <Film size={24} className="mx-auto mb-1 text-cyber-accent" />
                      <p className="text-2xl font-bold">{libraryData.movieCount}</p>
                      <p className="text-xs text-gray-400">Movies</p>
                    </div>
                    <div className="text-center p-3 bg-cyber-darker rounded-lg">
                      <Tv size={24} className="mx-auto mb-1 text-cyber-accent" />
                      <p className="text-2xl font-bold">{libraryData.showCount}</p>
                      <p className="text-xs text-gray-400">TV Shows</p>
                    </div>
                    <div className="text-center p-3 bg-cyber-darker rounded-lg">
                      <AlertTriangle size={24} className="mx-auto mb-1 text-cyber-yellow" />
                      <p className="text-2xl font-bold">{libraryData.duplicates}</p>
                      <p className="text-xs text-gray-400">Duplicates</p>
                    </div>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        )

      case 'services':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-2">Connect Your Services</h2>
              <p className="text-gray-400">Configure your media management tools (all optional)</p>
            </div>

            {/* Radarr */}
            <ServiceRow
              name="Radarr"
              icon={Film}
              description="Movie management"
              fields={[
                { key: 'url', label: 'URL', placeholder: 'http://192.168.1.100:7878', value: services.radarr.url },
                { key: 'api_key', label: 'API Key', placeholder: 'API Key', value: services.radarr.api_key, type: 'password' },
              ]}
              onChange={(field, value) => updateService('radarr', field, value)}
              onTest={() => testService('radarr')}
              testing={services.radarr.testing}
              connected={services.radarr.connected}
              result={services.radarr.result}
            />

            {/* Sonarr */}
            <ServiceRow
              name="Sonarr"
              icon={Tv}
              description="TV show management"
              fields={[
                { key: 'url', label: 'URL', placeholder: 'http://192.168.1.100:8989', value: services.sonarr.url },
                { key: 'api_key', label: 'API Key', placeholder: 'API Key', value: services.sonarr.api_key, type: 'password' },
              ]}
              onChange={(field, value) => updateService('sonarr', field, value)}
              onTest={() => testService('sonarr')}
              testing={services.sonarr.testing}
              connected={services.sonarr.connected}
              result={services.sonarr.result}
            />

            {/* Overseerr */}
            <ServiceRow
              name="Overseerr"
              icon={Bell}
              description="Request management"
              fields={[
                { key: 'url', label: 'URL', placeholder: 'http://192.168.1.100:5055', value: services.overseerr.url },
                { key: 'api_key', label: 'API Key', placeholder: 'API Key', value: services.overseerr.api_key, type: 'password' },
              ]}
              onChange={(field, value) => updateService('overseerr', field, value)}
              onTest={() => testService('overseerr')}
              testing={services.overseerr.testing}
              connected={services.overseerr.connected}
              result={services.overseerr.result}
            />

            {/* Tautulli */}
            <ServiceRow
              name="Tautulli"
              icon={BarChart}
              description="Watch history & stats"
              fields={[
                { key: 'url', label: 'URL', placeholder: 'http://192.168.1.100:8181', value: services.tautulli.url },
                { key: 'api_key', label: 'API Key', placeholder: 'API Key', value: services.tautulli.api_key, type: 'password' },
              ]}
              onChange={(field, value) => updateService('tautulli', field, value)}
              onTest={() => testService('tautulli')}
              testing={services.tautulli.testing}
              connected={services.tautulli.connected}
              result={services.tautulli.result}
            />

            {/* FileBot */}
            <ServiceRow
              name="FileBot"
              icon={FileText}
              description="File organization"
              fields={[
                { key: 'url', label: 'URL', placeholder: 'http://192.168.1.100:5452', value: services.filebot.url },
                { key: 'username', label: 'Username', placeholder: 'Optional', value: services.filebot.username },
                { key: 'password', label: 'Password', placeholder: 'Optional', value: services.filebot.password, type: 'password' },
              ]}
              onChange={(field, value) => updateService('filebot', field, value)}
              onTest={() => testService('filebot')}
              testing={services.filebot.testing}
              connected={services.filebot.connected}
              result={services.filebot.result}
            />
          </div>
        )

      case 'ai':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <Sparkles className="text-cyber-accent mx-auto mb-3" size={40} />
              <h2 className="text-2xl font-bold mb-2">AI Configuration</h2>
              <p className="text-gray-400">Power your library curation with AI</p>
            </div>

            {/* Cloud AI Providers */}
            <div className="cyber-card space-y-4">
              <h3 className="font-semibold flex items-center gap-2">
                <Sparkles size={18} className="text-cyber-accent" />
                Cloud AI Providers
              </h3>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Anthropic API Key (Recommended)</label>
                <input
                  type="password"
                  placeholder="sk-ant-api..."
                  value={ai.anthropic_api_key}
                  onChange={(e) => setAi(prev => ({ ...prev, anthropic_api_key: e.target.value }))}
                  className="cyber-input"
                />
                <p className="text-xs text-gray-500 mt-1">Powers Claude for intelligent curation</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">OpenAI API Key (Alternative)</label>
                <input
                  type="password"
                  placeholder="sk-..."
                  value={ai.openai_api_key}
                  onChange={(e) => setAi(prev => ({ ...prev, openai_api_key: e.target.value }))}
                  className="cyber-input"
                />
              </div>

              <button
                onClick={saveAiConfig}
                disabled={!ai.anthropic_api_key && !ai.openai_api_key}
                className="cyber-button w-full"
              >
                {aiSaved ? (
                  <>
                    <Check size={18} className="mr-2" />
                    Saved
                  </>
                ) : (
                  'Save API Keys'
                )}
              </button>
            </div>

            {/* Local LLM */}
            <div className="cyber-card space-y-4">
              <h3 className="font-semibold flex items-center gap-2">
                <Download size={18} className="text-cyber-accent" />
                Free Local AI (No API Key Required)
              </h3>

              <div className="p-4 bg-cyber-darker rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <p className="font-medium">{localLlm.modelName}</p>
                    <p className="text-sm text-gray-400">{localLlm.modelSize} download</p>
                  </div>

                  {localLlm.installed ? (
                    <span className="flex items-center gap-1 text-cyber-green">
                      <Check size={16} />
                      Installed
                    </span>
                  ) : localLlm.downloading ? (
                    <span className="text-cyber-accent">
                      {localLlm.downloadProgress}%
                    </span>
                  ) : null}
                </div>

                {localLlm.downloading && (
                  <div className="w-full bg-cyber-dark rounded-full h-2 mb-3">
                    <div
                      className="bg-cyber-accent h-2 rounded-full transition-all duration-300"
                      style={{ width: `${localLlm.downloadProgress}%` }}
                    />
                  </div>
                )}

                {!localLlm.installed && (
                  <button
                    onClick={downloadLocalLlm}
                    disabled={localLlm.downloading}
                    className="cyber-button-primary w-full"
                  >
                    {localLlm.downloading ? (
                      <>
                        <Loader2 size={18} className="mr-2 animate-spin" />
                        Downloading...
                      </>
                    ) : (
                      <>
                        <Download size={18} className="mr-2" />
                        Download Free AI Model
                      </>
                    )}
                  </button>
                )}
              </div>

              <p className="text-xs text-gray-500">
                The local model runs entirely on your server. No data is sent externally.
              </p>
            </div>

            {/* What AI Does */}
            <div className="p-4 border border-cyber-accent/30 bg-cyber-accent/5 rounded-xl">
              <h4 className="font-medium text-cyber-accent mb-2">After setup, AI will analyze your library to:</h4>
              <ul className="text-sm text-gray-400 space-y-1">
                <li className="flex items-center gap-2">
                  <Check size={14} className="text-cyber-green" />
                  Identify ~20 movies you should add based on your taste
                </li>
                <li className="flex items-center gap-2">
                  <Check size={14} className="text-cyber-green" />
                  Find "bad" movies with low ratings to consider removing
                </li>
                <li className="flex items-center gap-2">
                  <Check size={14} className="text-cyber-green" />
                  Detect duplicate files and quality issues
                </li>
                <li className="flex items-center gap-2">
                  <Check size={14} className="text-cyber-green" />
                  Recommend TV shows and anime based on your collection
                </li>
              </ul>
            </div>
          </div>
        )
    }
  }

  const canProceed = currentStep === 0 ? plexConnected : true

  return (
    <div className="min-h-screen bg-cyber-dark cyber-grid flex flex-col">
      {/* Progress bar */}
      <div className="h-1 bg-cyber-darker">
        <div
          className="h-full bg-cyber-accent transition-all duration-300"
          style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
        />
      </div>

      {/* Steps indicator */}
      <div className="border-b border-cyber-border bg-cyber-panel/50">
        <div className="max-w-3xl mx-auto px-6 py-4">
          <div className="flex items-center justify-center gap-8">
            {steps.map((step, index) => (
              <div
                key={step.id}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                  index === currentStep
                    ? 'bg-cyber-accent/10 text-cyber-accent'
                    : index < currentStep
                      ? 'text-cyber-green'
                      : 'text-gray-600'
                }`}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold ${
                  index < currentStep ? 'bg-cyber-green text-cyber-dark' :
                  index === currentStep ? 'bg-cyber-accent text-cyber-dark' : 'bg-gray-700'
                }`}>
                  {index < currentStep ? <Check size={14} /> : index + 1}
                </div>
                <step.icon size={18} />
                <span className="font-medium">{step.title}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-start justify-center p-6 overflow-y-auto">
        <div className="w-full max-w-2xl py-4">
          {renderStep()}
        </div>
      </div>

      {/* Navigation */}
      <div className="border-t border-cyber-border bg-cyber-panel/50">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={prevStep}
            disabled={currentStep === 0}
            className="cyber-button disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={18} className="mr-1" />
            Back
          </button>

          {currentStep < steps.length - 1 ? (
            <button
              onClick={nextStep}
              disabled={!canProceed}
              className="cyber-button-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
              <ChevronRight size={18} className="ml-1" />
            </button>
          ) : (
            <button
              onClick={completeSetup}
              className="cyber-button-primary"
            >
              Complete Setup
              <ArrowRight size={18} className="ml-1" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// Service row component for the services page
function ServiceRow({ name, icon: Icon, description, fields, onChange, onTest, testing, connected, result }) {
  const [expanded, setExpanded] = useState(false)
  const hasInput = fields.some(f => f.value)

  return (
    <div className="cyber-card">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <Icon size={20} className="text-cyber-accent" />
          <div>
            <p className="font-medium">{name}</p>
            <p className="text-xs text-gray-500">{description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {connected && <Check size={18} className="text-cyber-green" />}
          <ChevronRight
            size={18}
            className={`text-gray-400 transition-transform ${expanded ? 'rotate-90' : ''}`}
          />
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-cyber-border space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {fields.map(field => (
              <div key={field.key}>
                <input
                  type={field.type || 'text'}
                  placeholder={field.placeholder}
                  value={field.value}
                  onChange={(e) => onChange(field.key, e.target.value)}
                  className="cyber-input text-sm"
                />
              </div>
            ))}
          </div>

          {result && (
            <div className={`p-2 rounded text-sm ${result.success ? 'bg-cyber-green/10 text-cyber-green' : 'bg-cyber-red/10 text-cyber-red'}`}>
              {result.message}
            </div>
          )}

          <button
            onClick={(e) => { e.stopPropagation(); onTest(); }}
            disabled={testing || !hasInput}
            className="cyber-button text-sm w-full"
          >
            {testing ? (
              <>
                <RefreshCw size={14} className="mr-1 animate-spin" />
                Testing...
              </>
            ) : connected ? (
              <>
                <Check size={14} className="mr-1" />
                Connected
              </>
            ) : (
              'Test Connection'
            )}
          </button>
        </div>
      )}
    </div>
  )
}
