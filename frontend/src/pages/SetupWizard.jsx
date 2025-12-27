import { useState } from 'react'
import { 
  Server, Film, Tv, Bell, BarChart, FileText, Sparkles, 
  ChevronRight, ChevronLeft, Check, X, RefreshCw, ArrowRight
} from 'lucide-react'
import { api } from '../services/api'

const steps = [
  { id: 'welcome', title: 'Welcome', icon: Sparkles },
  { id: 'plex', title: 'Plex', icon: Server, required: true },
  { id: 'radarr', title: 'Radarr', icon: Film },
  { id: 'sonarr', title: 'Sonarr', icon: Tv },
  { id: 'overseerr', title: 'Overseerr', icon: Bell },
  { id: 'tautulli', title: 'Tautulli', icon: BarChart },
  { id: 'filebot', title: 'FileBot', icon: FileText },
  { id: 'ai', title: 'AI Setup', icon: Sparkles },
  { id: 'complete', title: 'Complete', icon: Check },
]

export default function SetupWizard({ onComplete }) {
  const [currentStep, setCurrentStep] = useState(0)
  const [configuredServices, setConfiguredServices] = useState({})
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  
  // Form states for each service
  const [plex, setPlex] = useState({ url: '', token: '' })
  const [radarr, setRadarr] = useState({ url: '', api_key: '' })
  const [sonarr, setSonarr] = useState({ url: '', api_key: '' })
  const [overseerr, setOverseerr] = useState({ url: '', api_key: '' })
  const [tautulli, setTautulli] = useState({ url: '', api_key: '' })
  const [filebot, setFilebot] = useState({ url: '', username: '', password: '' })
  const [ai, setAi] = useState({ anthropic_api_key: '', openai_api_key: '', ollama_url: '' })

  const testAndConfigure = async (service, endpoint, data) => {
    setTesting(true)
    setTestResult(null)

    try {
      // Test connection - api.post returns JSON directly (not wrapped in .data)
      const testResponse = await api.post(`/api/setup/test/${service}`, data)

      if (testResponse.success) {
        // Configure
        await api.post(`/api/setup/configure/${service}`, data)
        setConfiguredServices(prev => ({ ...prev, [service]: true }))
        setTestResult({ success: true, message: testResponse.message })
      } else {
        setTestResult({ success: false, message: testResponse.message })
      }
    } catch (error) {
      setTestResult({ success: false, message: error.message })
    } finally {
      setTesting(false)
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
      setTestResult(null)
    }
  }

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
      setTestResult(null)
    }
  }

  const skipStep = () => {
    nextStep()
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
            <p className="text-sm text-cyber-accent/60 font-mono mb-4">v2512.1.0</p>
            <p className="text-lg text-gray-400 max-w-lg mx-auto mb-8">
              Your AI-powered Plex library management system. Let's get you set up in just a few minutes.
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
          <ServiceSetupStep
            title="Connect to Plex"
            description="Plex is required for Butlarr to work. Enter your server details below."
            required={true}
            fields={[
              { key: 'url', label: 'Server URL', value: plex.url, onChange: (v) => setPlex(p => ({ ...p, url: v })), placeholder: 'http://192.168.1.100:32400' },
              { key: 'token', label: 'X-Plex-Token', value: plex.token, onChange: (v) => setPlex(p => ({ ...p, token: v })), placeholder: 'Your Plex authentication token', type: 'password' },
            ]}
            helpText="You can find your Plex token in the XML of any library item URL or in the Plex Web App developer console."
            onTest={() => testAndConfigure('plex', '/api/setup/test/plex', plex)}
            testing={testing}
            testResult={testResult}
            configured={configuredServices.plex}
          />
        )

      case 'radarr':
        return (
          <ServiceSetupStep
            title="Connect to Radarr"
            description="Radarr enables movie management and deletion capabilities."
            fields={[
              { key: 'url', label: 'Server URL', value: radarr.url, onChange: (v) => setRadarr(p => ({ ...p, url: v })), placeholder: 'http://192.168.1.100:7878' },
              { key: 'api_key', label: 'API Key', value: radarr.api_key, onChange: (v) => setRadarr(p => ({ ...p, api_key: v })), placeholder: 'Radarr API key', type: 'password' },
            ]}
            helpText="Find your API key in Radarr under Settings → General → Security."
            onTest={() => testAndConfigure('radarr', '/api/setup/test/radarr', radarr)}
            testing={testing}
            testResult={testResult}
            configured={configuredServices.radarr}
          />
        )

      case 'sonarr':
        return (
          <ServiceSetupStep
            title="Connect to Sonarr"
            description="Sonarr enables TV show management and organization."
            fields={[
              { key: 'url', label: 'Server URL', value: sonarr.url, onChange: (v) => setSonarr(p => ({ ...p, url: v })), placeholder: 'http://192.168.1.100:8989' },
              { key: 'api_key', label: 'API Key', value: sonarr.api_key, onChange: (v) => setSonarr(p => ({ ...p, api_key: v })), placeholder: 'Sonarr API key', type: 'password' },
            ]}
            helpText="Find your API key in Sonarr under Settings → General → Security."
            onTest={() => testAndConfigure('sonarr', '/api/setup/test/sonarr', sonarr)}
            testing={testing}
            testResult={testResult}
            configured={configuredServices.sonarr}
          />
        )

      case 'overseerr':
        return (
          <ServiceSetupStep
            title="Connect to Overseerr"
            description="Overseerr integration protects user-requested content and enables request sending."
            fields={[
              { key: 'url', label: 'Server URL', value: overseerr.url, onChange: (v) => setOverseerr(p => ({ ...p, url: v })), placeholder: 'http://192.168.1.100:5055' },
              { key: 'api_key', label: 'API Key', value: overseerr.api_key, onChange: (v) => setOverseerr(p => ({ ...p, api_key: v })), placeholder: 'Overseerr API key', type: 'password' },
            ]}
            helpText="Find your API key in Overseerr under Settings → General."
            onTest={() => testAndConfigure('overseerr', '/api/setup/test/overseerr', overseerr)}
            testing={testing}
            testResult={testResult}
            configured={configuredServices.overseerr}
          />
        )

      case 'tautulli':
        return (
          <ServiceSetupStep
            title="Connect to Tautulli"
            description="Tautulli provides watch history data (disabled by default for privacy)."
            fields={[
              { key: 'url', label: 'Server URL', value: tautulli.url, onChange: (v) => setTautulli(p => ({ ...p, url: v })), placeholder: 'http://192.168.1.100:8181' },
              { key: 'api_key', label: 'API Key', value: tautulli.api_key, onChange: (v) => setTautulli(p => ({ ...p, api_key: v })), placeholder: 'Tautulli API key', type: 'password' },
            ]}
            helpText="Find your API key in Tautulli under Settings → Web Interface."
            onTest={() => testAndConfigure('tautulli', '/api/setup/test/tautulli', tautulli)}
            testing={testing}
            testResult={testResult}
            configured={configuredServices.tautulli}
          />
        )

      case 'filebot':
        return (
          <ServiceSetupStep
            title="Connect to FileBot Node"
            description="FileBot Node enables automated file renaming and organization."
            fields={[
              { key: 'url', label: 'Server URL', value: filebot.url, onChange: (v) => setFilebot(p => ({ ...p, url: v })), placeholder: 'http://192.168.1.100:5452' },
              { key: 'username', label: 'Username (optional)', value: filebot.username, onChange: (v) => setFilebot(p => ({ ...p, username: v })), placeholder: 'Username' },
              { key: 'password', label: 'Password (optional)', value: filebot.password, onChange: (v) => setFilebot(p => ({ ...p, password: v })), placeholder: 'Password', type: 'password' },
            ]}
            helpText="FileBot Node runs as a Docker container. See the FileBot Node documentation for setup."
            onTest={() => testAndConfigure('filebot', '/api/setup/test/filebot', filebot)}
            testing={testing}
            testResult={testResult}
            configured={configuredServices.filebot}
          />
        )

      case 'ai':
        return (
          <div className="space-y-6">
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
              <p className="text-xs text-gray-500 mt-2">Powers GPT-5 Mini for budget-friendly curation.</p>
            </div>

            <div className="cyber-card">
              <h3 className="font-semibold mb-4">Ollama (Free, Local)</h3>
              <input 
                type="text"
                placeholder="http://host.docker.internal:11434"
                value={ai.ollama_url}
                onChange={(e) => setAi(prev => ({ ...prev, ollama_url: e.target.value }))}
                className="cyber-input"
              />
              <p className="text-xs text-gray-500 mt-2">Run AI models locally for free assistant chat.</p>
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
              {Object.entries(configuredServices).map(([service, configured]) => (
                <div key={service} className="cyber-card text-center">
                  {configured ? (
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
    }
  }

  const currentStepData = steps[currentStep]
  const canProceed = currentStepData.id === 'welcome' || 
                     currentStepData.id === 'complete' ||
                     !currentStepData.required || 
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
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-2xl">
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
            {!currentStepData.required && currentStep > 0 && currentStep < steps.length - 1 && (
              <button onClick={skipStep} className="text-gray-400 hover:text-white transition-colors">
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

function ServiceSetupStep({ title, description, fields, helpText, onTest, testing, testResult, configured, required }) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold mb-2">{title}</h2>
        <p className="text-gray-400">{description}</p>
        {required && <span className="cyber-badge-warning mt-2">Required</span>}
      </div>

      <div className="cyber-card space-y-4">
        {fields.map((field) => (
          <div key={field.key}>
            <label className="block text-sm font-medium text-gray-400 mb-1">{field.label}</label>
            <input 
              type={field.type || 'text'}
              placeholder={field.placeholder}
              value={field.value}
              onChange={(e) => field.onChange(e.target.value)}
              className="cyber-input"
            />
          </div>
        ))}

        {helpText && (
          <p className="text-xs text-gray-500">{helpText}</p>
        )}

        {testResult && (
          <div className={`p-3 rounded-lg ${testResult.success ? 'bg-cyber-green/10 border border-cyber-green/30' : 'bg-cyber-red/10 border border-cyber-red/30'}`}>
            <div className="flex items-center gap-2">
              {testResult.success ? <Check className="text-cyber-green" size={18} /> : <X className="text-cyber-red" size={18} />}
              <span className={testResult.success ? 'text-cyber-green' : 'text-cyber-red'}>{testResult.message}</span>
            </div>
          </div>
        )}

        <button 
          onClick={onTest}
          disabled={testing}
          className="cyber-button-primary w-full"
        >
          {testing ? (
            <>
              <RefreshCw size={18} className="mr-2 animate-spin" />
              Testing...
            </>
          ) : configured ? (
            <>
              <Check size={18} className="mr-2" />
              Connected - Test Again
            </>
          ) : (
            'Test & Connect'
          )}
        </button>
      </div>
    </div>
  )
}
