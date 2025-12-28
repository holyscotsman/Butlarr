import React, { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  RefreshCw,
  Check,
  AlertCircle,
  Download,
  Server,
  GitBranch,
  Wifi,
  WifiOff,
  Zap,
  Bot,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Loader2
} from 'lucide-react';

export default function Settings() {
  const [systemInfo, setSystemInfo] = useState(null);
  const [updateStatus, setUpdateStatus] = useState(null);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [testing, setTesting] = useState({});

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [infoRes, settingsRes] = await Promise.all([
        fetch('/api/system/info'),
        fetch('/api/settings'),
      ]);

      if (infoRes.ok) {
        setSystemInfo(await infoRes.json());
      }
      if (settingsRes.ok) {
        setSettings(await settingsRes.json());
      }
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const checkForUpdates = async () => {
    setCheckingUpdate(true);
    try {
      const res = await fetch('/api/system/update/check');
      if (res.ok) {
        setUpdateStatus(await res.json());
      }
    } catch (error) {
      console.error('Failed to check updates:', error);
    } finally {
      setCheckingUpdate(false);
    }
  };

  const applyUpdate = async () => {
    if (!confirm('Apply update? The app will need to be restarted after the update completes.')) {
      return;
    }

    setUpdating(true);
    try {
      const res = await fetch('/api/system/update/apply', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        alert(data.message);
      } else {
        const error = await res.json();
        alert(`Update failed: ${error.detail}`);
      }
    } catch (error) {
      alert(`Update failed: ${error.message}`);
    } finally {
      setUpdating(false);
    }
  };

  const saveSettings = async () => {
    setSaveStatus('saving');
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });

      if (res.ok) {
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 5000);
      } else {
        setSaveStatus('error');
        setTimeout(() => setSaveStatus(null), 5000);
      }
    } catch (error) {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus(null), 5000);
    }
  };

  const testConnection = async (service) => {
    setTesting(prev => ({ ...prev, [service]: true }));
    setTestResults(prev => ({ ...prev, [service]: null }));

    try {
      let endpoint = '';
      let body = {};

      switch (service) {
        case 'plex':
          endpoint = '/api/setup/test/plex';
          body = { url: settings.plex?.url, token: settings.plex?.token };
          break;
        case 'radarr':
          endpoint = '/api/setup/test/radarr';
          body = { url: settings.radarr?.url, api_key: settings.radarr?.api_key };
          break;
        case 'sonarr':
          endpoint = '/api/setup/test/sonarr';
          body = { url: settings.sonarr?.url, api_key: settings.sonarr?.api_key };
          break;
        case 'bazarr':
          endpoint = '/api/setup/test/bazarr';
          body = { url: settings.bazarr?.url, api_key: settings.bazarr?.api_key };
          break;
        case 'ollama':
          endpoint = '/api/setup/test/ai';
          body = { ollama_url: settings.ai?.ollama_url };
          break;
        default:
          return;
      }

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      setTestResults(prev => ({
        ...prev,
        [service]: { success: data.success, message: data.message }
      }));
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [service]: { success: false, message: error.message }
      }));
    } finally {
      setTesting(prev => ({ ...prev, [service]: false }));
    }
  };

  const updateSetting = (section, key, value) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value,
      },
    }));
  };

  const TestButton = ({ service, disabled }) => (
    <button
      onClick={() => testConnection(service)}
      disabled={disabled || testing[service]}
      className="px-3 py-2 bg-cyber-accent/10 hover:bg-cyber-accent/20 border border-cyber-accent/50 rounded-lg text-cyber-accent text-sm flex items-center gap-2 disabled:opacity-50 transition-all"
    >
      {testing[service] ? (
        <Loader2 size={16} className="animate-spin" />
      ) : testResults[service]?.success ? (
        <CheckCircle2 size={16} className="text-cyber-green" />
      ) : testResults[service]?.success === false ? (
        <XCircle size={16} className="text-cyber-red" />
      ) : (
        <Wifi size={16} />
      )}
      Test
    </button>
  );

  const StatusBadge = ({ service }) => {
    const result = testResults[service];
    if (!result) return null;

    return (
      <div className={`text-xs mt-1 ${result.success ? 'text-cyber-green' : 'text-cyber-red'}`}>
        {result.message}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-cyber-accent" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3">
        <SettingsIcon className="w-8 h-8 text-cyber-accent" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>

      {/* Save Status Banner */}
      {saveStatus && (
        <div className={`p-4 rounded-lg flex items-center gap-3 ${
          saveStatus === 'saving' ? 'bg-cyber-accent/20 border border-cyber-accent/50' :
          saveStatus === 'success' ? 'bg-cyber-green/20 border border-cyber-green/50' :
          'bg-cyber-red/20 border border-cyber-red/50'
        }`}>
          {saveStatus === 'saving' && <Loader2 className="w-5 h-5 animate-spin text-cyber-accent" />}
          {saveStatus === 'success' && <CheckCircle2 className="w-5 h-5 text-cyber-green" />}
          {saveStatus === 'error' && <XCircle className="w-5 h-5 text-cyber-red" />}
          <span className={
            saveStatus === 'saving' ? 'text-cyber-accent' :
            saveStatus === 'success' ? 'text-cyber-green' :
            'text-cyber-red'
          }>
            {saveStatus === 'saving' && 'Saving settings...'}
            {saveStatus === 'success' && 'Settings saved successfully!'}
            {saveStatus === 'error' && 'Failed to save settings. Please try again.'}
          </span>
        </div>
      )}

      {/* System Info Card */}
      <div className="cyber-card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Server className="w-5 h-5 text-cyber-accent" />
          System Information
        </h2>

        {systemInfo && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-cyber-darker rounded-lg p-3">
              <div className="text-sm text-gray-400">Version</div>
              <div className="text-lg font-mono text-cyber-accent">{systemInfo.version}</div>
            </div>
            <div className="bg-cyber-darker rounded-lg p-3">
              <div className="text-sm text-gray-400">Git Commit</div>
              <div className="text-lg font-mono">{systemInfo.git_commit || 'N/A'}</div>
            </div>
            <div className="bg-cyber-darker rounded-lg p-3">
              <div className="text-sm text-gray-400">Branch</div>
              <div className="text-lg font-mono">{systemInfo.git_branch || 'N/A'}</div>
            </div>
            <div className="bg-cyber-darker rounded-lg p-3">
              <div className="text-sm text-gray-400">Uptime</div>
              <div className="text-lg font-mono">
                {Math.floor(systemInfo.uptime_seconds / 3600)}h {Math.floor((systemInfo.uptime_seconds % 3600) / 60)}m
              </div>
            </div>
          </div>
        )}

        {/* AI Providers Status */}
        {systemInfo && (
          <div className="mt-4">
            <div className="text-sm text-gray-400 mb-2">Active AI Providers</div>
            <div className="flex flex-wrap gap-2">
              {systemInfo.ai_providers.map(provider => (
                <span
                  key={provider}
                  className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-2 ${
                    provider === 'embedded'
                      ? 'bg-cyber-green/20 text-cyber-green border border-cyber-green/30'
                      : 'bg-cyber-accent/20 text-cyber-accent border border-cyber-accent/30'
                  }`}
                >
                  {provider === 'embedded' ? <Bot size={14} /> : <Zap size={14} />}
                  {provider === 'embedded' ? 'Embedded AI (Qwen 2.5)' : provider.charAt(0).toUpperCase() + provider.slice(1)}
                </span>
              ))}
              {systemInfo.ai_providers.length === 0 && (
                <span className="text-cyber-yellow flex items-center gap-2">
                  <WifiOff size={14} />
                  No AI providers configured
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Update Card */}
      <div className="cyber-card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <GitBranch className="w-5 h-5 text-cyber-accent" />
          Updates
        </h2>

        <div className="flex items-center gap-4">
          <button
            onClick={checkForUpdates}
            disabled={checkingUpdate}
            className="cyber-button"
          >
            <RefreshCw className={`w-4 h-4 ${checkingUpdate ? 'animate-spin' : ''}`} />
            Check for Updates
          </button>

          {updateStatus?.available && (
            <button
              onClick={applyUpdate}
              disabled={updating}
              className="cyber-button-primary"
            >
              <Download className={`w-4 h-4 ${updating ? 'animate-bounce' : ''}`} />
              {updating ? 'Updating...' : 'Apply Update'}
            </button>
          )}
        </div>

        {updateStatus && (
          <div className={`mt-4 p-4 rounded-lg ${
            updateStatus.available ? 'bg-cyber-green/10 border border-cyber-green/30' : 'bg-cyber-darker'
          }`}>
            {updateStatus.available ? (
              <div className="flex items-center gap-2 text-cyber-green">
                <AlertCircle className="w-5 h-5" />
                Update available! Latest commit: {updateStatus.latest_commit}
              </div>
            ) : (
              <div className="flex items-center gap-2 text-gray-400">
                <Check className="w-5 h-5" />
                {updateStatus.message}
              </div>
            )}
          </div>
        )}

        <p className="mt-4 text-sm text-gray-500">
          Auto-update is {systemInfo?.auto_update_enabled ? 'enabled' : 'disabled'}.
          Updates are checked on container restart.
        </p>
      </div>

      {/* Service Connections */}
      <div className="cyber-card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Wifi className="w-5 h-5 text-cyber-accent" />
          Service Connections
        </h2>

        <div className="space-y-6">
          {/* Plex */}
          <div className="p-4 bg-cyber-darker rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-cyber-accent">Plex Media Server</h3>
              <TestButton service="plex" disabled={!settings.plex?.url || !settings.plex?.token} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Server URL</label>
                <input
                  type="text"
                  value={settings.plex?.url || ''}
                  onChange={(e) => updateSetting('plex', 'url', e.target.value)}
                  placeholder="http://192.168.1.100:32400"
                  className="cyber-input"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Token</label>
                <input
                  type="password"
                  value={settings.plex?.token || ''}
                  onChange={(e) => updateSetting('plex', 'token', e.target.value)}
                  placeholder="Your Plex token"
                  className="cyber-input"
                />
              </div>
            </div>
            <StatusBadge service="plex" />
          </div>

          {/* Radarr */}
          <div className="p-4 bg-cyber-darker rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-cyber-accent">Radarr (Movies)</h3>
              <TestButton service="radarr" disabled={!settings.radarr?.url || !settings.radarr?.api_key} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">URL</label>
                <input
                  type="text"
                  value={settings.radarr?.url || ''}
                  onChange={(e) => updateSetting('radarr', 'url', e.target.value)}
                  placeholder="http://192.168.1.100:7878"
                  className="cyber-input"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">API Key</label>
                <input
                  type="password"
                  value={settings.radarr?.api_key || ''}
                  onChange={(e) => updateSetting('radarr', 'api_key', e.target.value)}
                  placeholder="API key from Radarr settings"
                  className="cyber-input"
                />
              </div>
            </div>
            <StatusBadge service="radarr" />
          </div>

          {/* Sonarr */}
          <div className="p-4 bg-cyber-darker rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-cyber-accent">Sonarr (TV Shows)</h3>
              <TestButton service="sonarr" disabled={!settings.sonarr?.url || !settings.sonarr?.api_key} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">URL</label>
                <input
                  type="text"
                  value={settings.sonarr?.url || ''}
                  onChange={(e) => updateSetting('sonarr', 'url', e.target.value)}
                  placeholder="http://192.168.1.100:8989"
                  className="cyber-input"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">API Key</label>
                <input
                  type="password"
                  value={settings.sonarr?.api_key || ''}
                  onChange={(e) => updateSetting('sonarr', 'api_key', e.target.value)}
                  placeholder="API key from Sonarr settings"
                  className="cyber-input"
                />
              </div>
            </div>
            <StatusBadge service="sonarr" />
          </div>

          {/* Bazarr */}
          <div className="p-4 bg-cyber-darker rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-cyber-accent">Bazarr (Subtitles)</h3>
              <TestButton service="bazarr" disabled={!settings.bazarr?.url || !settings.bazarr?.api_key} />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">URL</label>
                <input
                  type="text"
                  value={settings.bazarr?.url || ''}
                  onChange={(e) => updateSetting('bazarr', 'url', e.target.value)}
                  placeholder="http://192.168.1.100:6767"
                  className="cyber-input"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">API Key</label>
                <input
                  type="password"
                  value={settings.bazarr?.api_key || ''}
                  onChange={(e) => updateSetting('bazarr', 'api_key', e.target.value)}
                  placeholder="API key from Bazarr settings"
                  className="cyber-input"
                />
              </div>
            </div>
            <StatusBadge service="bazarr" />
          </div>
        </div>
      </div>

      {/* AI Configuration */}
      <div className="cyber-card">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Bot className="w-5 h-5 text-cyber-accent" />
          AI Configuration
        </h2>

        <div className="space-y-6">
          {/* Embedded AI Info */}
          <div className="p-4 bg-cyber-green/10 border border-cyber-green/30 rounded-lg">
            <div className="flex items-start gap-3">
              <Bot className="w-5 h-5 text-cyber-green mt-0.5" />
              <div>
                <h4 className="font-medium text-cyber-green">Embedded AI (Free)</h4>
                <p className="text-sm text-gray-400 mt-1">
                  Butlarr includes a built-in AI model (Qwen 2.5 1.5B) that runs locally.
                  It's slower than cloud APIs but completely free and private.
                  {systemInfo?.embedded_ai_available ? (
                    <span className="text-cyber-green"> ✓ Model loaded and ready</span>
                  ) : (
                    <span className="text-cyber-yellow"> Downloading model on first use...</span>
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Cloud AI APIs */}
          <div className="p-4 bg-cyber-darker rounded-lg">
            <h4 className="font-medium text-cyber-accent mb-3 flex items-center gap-2">
              <Zap size={16} />
              Cloud AI APIs (Faster, Optional)
            </h4>
            <p className="text-sm text-gray-400 mb-4">
              For faster and more accurate results, you can optionally connect cloud AI providers.
              These will be used instead of the embedded AI when available.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Anthropic API Key</label>
                <input
                  type="password"
                  value={settings.ai?.anthropic_api_key || ''}
                  onChange={(e) => updateSetting('ai', 'anthropic_api_key', e.target.value)}
                  placeholder="sk-ant-..."
                  className="cyber-input"
                />
                <p className="text-xs text-gray-500 mt-1">Claude models - most recommended</p>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">OpenAI API Key</label>
                <input
                  type="password"
                  value={settings.ai?.openai_api_key || ''}
                  onChange={(e) => updateSetting('ai', 'openai_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="cyber-input"
                />
                <p className="text-xs text-gray-500 mt-1">GPT-4o models</p>
              </div>
            </div>
          </div>

          {/* External Ollama */}
          <div className="p-4 bg-cyber-darker rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h4 className="font-medium text-cyber-accent flex items-center gap-2">
                  <ExternalLink size={16} />
                  External Ollama Server (Optional)
                </h4>
                <p className="text-sm text-gray-400 mt-1">
                  Connect to your own Ollama server for local AI without cloud costs.
                  This is different from the built-in embedded AI.
                </p>
              </div>
              <TestButton service="ollama" disabled={!settings.ai?.ollama_url} />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Ollama Server URL</label>
              <input
                type="text"
                value={settings.ai?.ollama_url || ''}
                onChange={(e) => updateSetting('ai', 'ollama_url', e.target.value)}
                placeholder="http://192.168.1.100:11434"
                className="cyber-input"
              />
              <p className="text-xs text-gray-500 mt-1">
                Leave empty to use only embedded AI and cloud providers
              </p>
            </div>
            <StatusBadge service="ollama" />
          </div>
        </div>
      </div>

      {/* Save Button - Sticky */}
      <div className="sticky bottom-4 flex justify-end">
        <button
          onClick={saveSettings}
          disabled={saveStatus === 'saving'}
          className="cyber-button-primary shadow-lg"
        >
          {saveStatus === 'saving' ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Check className="w-4 h-4" />
          )}
          {saveStatus === 'saving' ? 'Saving...' : 'Save All Settings'}
        </button>
      </div>
    </div>
  );
}
