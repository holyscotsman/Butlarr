import { useState, useEffect } from 'react'
import {
  Server, Film, Tv, Bell, BarChart, FileText, Sparkles,
  ChevronRight, ChevronLeft, Check, X, RefreshCw, ArrowRight,
  Loader2, CheckCircle2, Subtitles, Library
} from 'lucide-react'
import { api, ws } from '../services/api'

// Simplified 5-step wizard flow with clear progression
const steps = [
  { id: 'welcome', title: 'Welcome', icon: Sparkles },
  { id: 'plex', title: 'Plex', icon: Server, required: true },
  { id: 'services', title: 'Services', icon: Film },
  { id: 'ai', title: 'AI Setup', icon: Sparkles },
  { id: 'complete', title: 'Complete', icon: Check },
]

export default function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(0)
  const [configuredServices, setConfiguredServices] = useState({})
  const [testing, setTesting] = useState({})
  const [testResults, setTestResults] = useState({})
  const [scanStarted, setScanStarted] = useState(false)
  const [scanProgress, setScanProgress] = useState(null)
  const [scanComplete, setScanComplete] = useState(false)
  const [scanError, setScanError] = useState(null)
  const [version, setVersion] = useState(null)

  // Form states for services
  const [plex, setPlex] = useState({ url: '', token: '' })
  const [radarr, setRadarr] = useState({ url: '', api_key: '' })
  const [sonarr, setSonarr] = useState({ url: '', api_key: '' })
  const [overseerr, setOverseerr] = useState({ url: '', api_key: '' })
  const [tautulli, setTautulli] = useState({ url: '', api_key: '' })
  const [bazarr, setBazarr] = useState({ url: '', api_key: '' })
  const [filebot, setFilebot] = useState({ url: '', username: '', password: '' })
  const [ai, setAi] = useState({ anthropic_api_key: '', openai_api_key: '' })

  // Fetch version on mount
  useEffect(() => {
    api.get('/api/system/info')
      .then(data => data && setVersion(data.version))
      .catch(() => {})
  }, [])

  // WebSocket for real-time scan progress
  useEffect(() => {
    if (scanStarted && !scanComplete) {
      ws.connect('scan', (data) => {
        if (data.type === 'scan_progress') {
          setScanProgress(data)
        } else if (data.type === 'scan_complete') {
          setScanComplete(true)
          setScanProgress(null)
        }
      })

      return () => ws.disconnect('scan')
    }
  }, [scanStarted, scanComplete])

  // Test and configure a single service
  const testService = async (service, data) => {
    setTesting(prev => ({ ...prev, [service]: true }))
    setTestResults(prev => ({ ...prev, [service]: null }))

    try {
      const response = await api.post(`/api/setup/test/${service}`, data)

      if (response.success) {
        await api.post(`/api/setup/configure/${service}`, data)
        setConfiguredServices(prev => ({ ...prev, [service]: true }))
        setTestResults(prev => ({ ...prev, [service]: { success: true, message: response.message } }))

        // Start background Library Sync after Plex is configured
        if (service === 'plex' && !scanStarted) {
          setScanStarted(true)
          setScanError(null)
          // Only run Phase 1 (Library Sync) during setup - gets movies, shows, episodes
          api.post('/api/scan/start', { phases: [1] })
            .catch((err) => {
              setScanError(err.message || 'Failed to start library scan')
              setScanStarted(false)
            })
        }

        return true
      } else {
        setTestResults(prev => ({ ...prev, [service]: { success: false, message: response.message } }))
        return false
      }
    } catch (error) {
      setTestResults(prev => ({ ...prev, [service]: { success: false, message: error.message } }))
      return false
    } finally {
      setTesting(prev => ({ ...prev, [service]: false }))
    }
  }

  const completeSetup = async () => {
    try {
      await api.post('/api/setup/complete', { confirm: true })
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

  // Service input component for the combined services page
  const ServiceInput = ({ title, icon: Icon, service, fields, state, setState, helpText }) => {
    const isConfigured = configuredServices[service]
    const isTesting = testing[service]
    const result = testResults[service]
    const hasValues = fields.every(f => f.required ? state[f.key] : true) && fields.some(f => state[f.key])

    return (
      <div className={`p-4 border rounded-lg transition-all ${
        isConfigured ? 'bg-cyber-green/5 border-cyber-green/30' : 'bg-cyber-darker border-cyber-border'
      }`}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Icon size={18} className={isConfigured ? 'text-cyber-green' : 'text-cyber-accent'} />
            <h4 className="font-medium">{title}</h4>
            {isConfigured && <CheckCircle2 size={16} className="text-cyber-green" />}
          </div>
          <button
            onClick={() => {
              const data = {}
              fields.forEach(f => { data[f.key] = state[f.key] })
              testService(service, data)
            }}
            disabled={!hasValues || isTesting}
            className="px-3 py-1.5 text-sm rounded-lg transition-all disabled:opacity-50 flex items-center gap-2
              bg-cyber-accent/10 hover:bg-cyber-accent/20 border border-cyber-accent/50 text-cyber-accent"
          >
            {isTesting ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
            {isConfigured ? 'Re-test' : 'Connect'}
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {fields.map(field => (
            <div key={field.key} className={field.fullWidth ? 'col-span-2' : ''}>
              <input
                type={field.type || 'text'}
                placeholder={field.placeholder}
                value={state[field.key] || ''}
                onChange={(e) => setState(prev => ({ ...prev, [field.key]: e.target.value }))}
                className="cyber-input text-sm py-2"
              />
            </div>
          ))}
        </div>

        {helpText && <p className="text-xs text-gray-500 mt-2">{helpText}</p>}

        {result && (
          <div className={`text-xs mt-2 ${result.success ? 'text-cyber-green' : 'text-cyber-red'}`}>
            {result.message}
          </div>
        )}
      </div>
    )
  }

  const renderStep = () => {
    const step = steps[currentStep]

    switch (step.id) {
      case 'welcome':
        return (
          <div className="text-center py-12">
            <div className="w-28 h-28 bg-cyber-accent rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-cyber-lg pulse-glow">
              <span className="text-cyber-dark font-bold text-6xl">B</span>
            </div>
            <h2 className="text-4xl font-bold mb-2 heading-glow">Welcome to Butlarr</h2>
            {version && <p className="text-sm text-cyber-accent/60 font-mono mb-4">v{version}</p>}
            <p className="text-lg text-gray-400 max-w-lg mx-auto mb-8">
              Your AI-powered Plex library management system. Let's get you set up in just a few steps.
            </p>
            <div className="space-y-4 text-left max-w-md mx-auto">
              <div className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg">
                <Check className="text-cyber-green" size={20} />
                <span>AI-powered recommendations and curation</span>
              </div>
              <div className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg">
                <Check className="text-cyber-green" size={20} />
                <span>Automated file organization with FileBot</span>
              </div>
              <div className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg">
                <Check className="text-cyber-green" size={20} />
                <span>Quality scanning and issue detection</span>
              </div>
              <div className="flex items-center gap-3 p-3 bg-cyber-darker rounded-lg">
                <Check className="text-cyber-green" size={20} />
                <span>Storage optimization and duplicate detection</span>
              </div>
            </div>
          </div>
        )

      case 'plex':
        return (
          <div className="space-y-6 max-w-lg mx-auto">
            <div className="text-center mb-8">
              <Server className="text-cyber-accent mx-auto mb-4" size={48} />
              <h2 className="text-2xl font-bold mb-2">Connect to Plex</h2>
              <p className="text-gray-400">Plex is required for Butlarr to work. Enter your server details below.</p>
              <span className="cyber-badge-warning mt-2">Required</span>
            </div>

            <div className="cyber-card space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">Server URL</label>
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
              </div>
              <p className="text-xs text-gray-500">
                You can find your Plex token in the XML of any library item URL or in the Plex Web App developer console.
              </p>

              {testResults.plex && (
                <div className={`p-3 rounded-lg ${testResults.plex.success ? 'bg-cyber-green/10 border border-cyber-green/30' : 'bg-cyber-red/10 border border-cyber-red/30'}`}>
                  <div className="flex items-center gap-2">
                    {testResults.plex.success ? <Check className="text-cyber-green" size={18} /> : <X className="text-cyber-red" size={18} />}
                    <span className={testResults.plex.success ? 'text-cyber-green' : 'text-cyber-red'}>{testResults.plex.message}</span>
                  </div>
                </div>
              )}

              <button
                onClick={() => testService('plex', plex)}
                disabled={testing.plex || !plex.url || !plex.token}
                className="cyber-button-primary w-full"
              >
                {testing.plex ? (
                  <>
                    <RefreshCw size={18} className="mr-2 animate-spin" />
                    Testing...
                  </>
                ) : configuredServices.plex ? (
                  <>
                    <Check size={18} className="mr-2" />
                    Connected - Test Again
                  </>
                ) : (
                  'Test & Connect'
                )}
              </button>
            </div>

            {(scanStarted || scanError) && (
              <div className={`p-4 rounded-lg border transition-all ${
                scanError
                  ? 'bg-cyber-red/10 border-cyber-red/30'
                  : scanComplete
                    ? 'bg-cyber-green/10 border-cyber-green/30'
                    : 'bg-cyber-accent/10 border-cyber-accent/30'
              }`}>
                <div className="flex items-center gap-2 mb-2">
                  {scanError ? (
                    <>
                      <X size={18} className="text-cyber-red" />
                      <span className="font-medium text-cyber-red">Scan failed: {scanError}</span>
                    </>
                  ) : scanComplete ? (
                    <>
                      <CheckCircle2 size={18} className="text-cyber-green" />
                      <span className="font-medium text-cyber-green">Library scan complete!</span>
                    </>
                  ) : (
                    <>
                      <Library size={18} className="text-cyber-accent animate-pulse" />
                      <span className="font-medium text-cyber-accent">Scanning your library...</span>
                    </>
                  )}
                </div>

                {!scanComplete && scanProgress && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-400">{scanProgress.phase_name || 'Initializing'}</span>
                      <span className="text-cyber-accent font-mono">{(scanProgress.progress_percent || 0).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 bg-cyber-darker rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyber-accent transition-all duration-300"
                        style={{ width: `${scanProgress.progress_percent || 0}%` }}
                      />
                    </div>
                    {scanProgress.current_item && (
                      <p className="text-xs text-gray-500 truncate">{scanProgress.current_item}</p>
                    )}
                  </div>
                )}

                {!scanComplete && !scanProgress && (
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Loader2 size={14} className="animate-spin" />
                    <span>Connecting to Plex...</span>
                  </div>
                )}

                <p className="text-sm text-gray-400 mt-3">
                  {scanComplete
                    ? 'Your library has been indexed. Continue to configure additional services.'
                    : 'You can continue with setup while the scan runs in the background.'}
                </p>
              </div>
            )}
          </div>
        )

      case 'services':
        return (
          <div className="space-y-6">
            <div className="text-center mb-6">
              <Film className="text-cyber-accent mx-auto mb-4" size={48} />
              <h2 className="text-2xl font-bold mb-2">Connect Your Services</h2>
              <p className="text-gray-400">Configure your media management services. All are optional - skip any you don't use.</p>
            </div>

            <div className="grid gap-4">
              <ServiceInput
                title="Radarr (Movies)"
                icon={Film}
                service="radarr"
                state={radarr}
                setState={setRadarr}
                fields={[
                  { key: 'url', placeholder: 'http://192.168.1.100:7878', required: true },
                  { key: 'api_key', placeholder: 'API Key', type: 'password', required: true },
                ]}
                helpText="Enables movie management and deletion capabilities"
              />

              <ServiceInput
                title="Sonarr (TV Shows)"
                icon={Tv}
                service="sonarr"
                state={sonarr}
                setState={setSonarr}
                fields={[
                  { key: 'url', placeholder: 'http://192.168.1.100:8989', required: true },
                  { key: 'api_key', placeholder: 'API Key', type: 'password', required: true },
                ]}
                helpText="Enables TV show management and organization"
              />

              <ServiceInput
                title="Overseerr (Requests)"
                icon={Bell}
                service="overseerr"
                state={overseerr}
                setState={setOverseerr}
                fields={[
                  { key: 'url', placeholder: 'http://192.168.1.100:5055', required: true },
                  { key: 'api_key', placeholder: 'API Key', type: 'password', required: true },
                ]}
                helpText="Protects user-requested content and enables request sending"
              />

              <ServiceInput
                title="Bazarr (Subtitles)"
                icon={Subtitles}
                service="bazarr"
                state={bazarr}
                setState={setBazarr}
                fields={[
                  { key: 'url', placeholder: 'http://192.168.1.100:6767', required: true },
                  { key: 'api_key', placeholder: 'API Key', type: 'password', required: true },
                ]}
                helpText="Enables subtitle management and automation"
              />

              <ServiceInput
                title="Tautulli (Analytics)"
                icon={BarChart}
                service="tautulli"
                state={tautulli}
                setState={setTautulli}
                fields={[
                  { key: 'url', placeholder: 'http://192.168.1.100:8181', required: true },
                  { key: 'api_key', placeholder: 'API Key', type: 'password', required: true },
                ]}
                helpText="Provides watch history data (disabled by default for privacy)"
              />

              <ServiceInput
                title="FileBot Node"
                icon={FileText}
                service="filebot"
                state={filebot}
                setState={setFilebot}
                fields={[
                  { key: 'url', placeholder: 'http://192.168.1.100:5452', required: true, fullWidth: true },
                  { key: 'username', placeholder: 'Username (optional)' },
                  { key: 'password', placeholder: 'Password (optional)', type: 'password' },
                ]}
                helpText="Enables automated file renaming and organization"
              />
            </div>
          </div>
        )

      case 'ai':
        return (
          <div className="space-y-6 max-w-lg mx-auto">
            <div className="text-center mb-8">
              <Sparkles className="text-cyber-accent mx-auto mb-4" size={48} />
              <h2 className="text-2xl font-bold mb-2">AI Configuration</h2>
              <p className="text-gray-400">Configure AI providers for library curation and assistant chat.</p>
            </div>

            <div className="cyber-card">
              <h3 className="font-semibold mb-4">Anthropic (Recommended)</h3>
              <input
                type="password"
                placeholder="sk-ant-api..."
                value={ai.anthropic_api_key}
                onChange={(e) => setAi(prev => ({ ...prev, anthropic_api_key: e.target.value }))}
                className="cyber-input"
              />
              <p className="text-xs text-gray-500 mt-2">Powers Claude Sonnet 4.5 for curation and Haiku for chat.</p>
            </div>

            <div className="cyber-card">
              <h3 className="font-semibold mb-4">OpenAI (Alternative)</h3>
              <input
                type="password"
                placeholder="sk-..."
                value={ai.openai_api_key}
                onChange={(e) => setAi(prev => ({ ...prev, openai_api_key: e.target.value }))}
                className="cyber-input"
              />
              <p className="text-xs text-gray-500 mt-2">Powers GPT-4o for budget-friendly curation.</p>
            </div>

            <div className="p-4 border border-cyber-accent/30 bg-cyber-accent/5 rounded-xl">
              <div className="flex items-center gap-3">
                <Sparkles className="text-cyber-accent" size={20} />
                <div>
                  <p className="text-cyber-accent font-medium">Free Local AI Available</p>
                  <p className="text-sm text-gray-400">You can download a free embedded AI model in Settings after setup.</p>
                </div>
              </div>
            </div>

            <button
              onClick={async () => {
                await api.post('/api/setup/configure/ai', ai)
                setConfiguredServices(prev => ({ ...prev, ai: true }))
              }}
              className="cyber-button-primary w-full"
            >
              Save AI Configuration
            </button>
          </div>
        )

      case 'complete':
        return (
          <div className="text-center py-12">
            <div className="w-24 h-24 bg-cyber-green rounded-full flex items-center justify-center mx-auto mb-6">
              <Check size={48} className="text-cyber-dark" />
            </div>
            <h2 className="text-3xl font-bold mb-4">Setup Complete!</h2>
            <p className="text-gray-400 max-w-lg mx-auto mb-8">
              Butlarr is ready to manage your Plex library. You can run your first scan from the dashboard.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 max-w-2xl mx-auto mb-8">
              {['plex', 'radarr', 'sonarr', 'overseerr', 'bazarr', 'tautulli', 'filebot', 'ai'].map((service) => (
                <div key={service} className="cyber-card text-center py-3">
                  {configuredServices[service] ? (
                    <Check className="text-cyber-green mx-auto" size={24} />
                  ) : (
                    <X className="text-gray-600 mx-auto" size={24} />
                  )}
                  <p className="text-sm mt-2 capitalize">{service}</p>
                </div>
              ))}
            </div>

            <button onClick={completeSetup} className="cyber-button-primary text-lg px-8 py-3">
              Go to Dashboard
              <ArrowRight className="ml-2" size={20} />
            </button>
          </div>
        )

      default:
        return null
    }
  }

  const currentStepData = steps[currentStep]
  const canProceed = currentStepData.id === 'welcome' ||
                     currentStepData.id === 'complete' ||
                     currentStepData.id === 'services' ||
                     currentStepData.id === 'ai' ||
                     configuredServices[currentStepData.id]

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
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-center gap-2 overflow-x-auto">
            {steps.map((step, index) => (
              <div
                key={step.id}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors ${
                  index === currentStep
                    ? 'bg-cyber-accent/10 text-cyber-accent'
                    : index < currentStep
                      ? 'text-cyber-green'
                      : 'text-gray-600'
                }`}
              >
                <step.icon size={16} />
                <span className="text-sm font-medium hidden sm:inline">{step.title}</span>
                {configuredServices[step.id] && <Check size={14} className="text-cyber-green" />}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="w-full max-w-3xl mx-auto">
          {renderStep()}
        </div>
      </div>

      {/* Navigation */}
      <div className="border-t border-cyber-border bg-cyber-panel/50">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <button
            onClick={prevStep}
            disabled={currentStep === 0}
            className="cyber-button disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft size={18} className="mr-1" />
            Back
          </button>

          <div className="flex gap-3">
            {currentStep > 0 && currentStep < steps.length - 1 && currentStepData.id !== 'plex' && (
              <button onClick={nextStep} className="text-gray-400 hover:text-white transition-colors">
                Skip for now
              </button>
            )}

            {currentStep < steps.length - 1 && (
              <button
                onClick={nextStep}
                disabled={!canProceed}
                className="cyber-button-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight size={18} className="ml-1" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
