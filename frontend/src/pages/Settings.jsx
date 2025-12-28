/**
 * Settings Page Component
 *
 * Displays and manages all application settings including:
 * - System information and version
 * - Service connections (Plex, Radarr, Sonarr, Bazarr, etc.)
 * - AI configuration (cloud APIs and local Ollama)
 * - Update management
 *
 * Note: Sensitive fields (tokens, API keys) are masked with '***' from the API.
 * When saving, masked values are preserved - only changed values are updated.
 */

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
import { api } from '../services/api';

// ============================================================================
// Reusable Components - Defined outside main component to prevent recreation
// ============================================================================

/**
 * Test connection button for services
 * Shows loading, success, or error state based on test results
 */
function TestButton({ service, disabled, testing, testResult, onTest }) {
  const isLoading = testing[service];
  const result = testResult[service];

  return (
    <button
      onClick={() => onTest(service)}
      disabled={disabled || isLoading}
      className="px-3 py-2 bg-cyber-accent/10 hover:bg-cyber-accent/20 border border-cyber-accent/50 rounded-lg text-cyber-accent text-sm flex items-center gap-2 disabled:opacity-50 transition-all"
    >
      {isLoading ? (
        <Loader2 size={16} className="animate-spin" />
      ) : result?.success ? (
        <CheckCircle2 size={16} className="text-cyber-green" />
      ) : result?.success === false ? (
        <XCircle size={16} className="text-cyber-red" />
      ) : (
        <Wifi size={16} />
      )}
      Test
    </button>
  );
}

/**
 * Status badge showing test result message
 */
function StatusBadge({ service, testResult }) {
  const result = testResult[service];
  if (!result) return null;

  return (
    <div className={`text-xs mt-1 ${result.success ? 'text-cyber-green' : 'text-cyber-red'}`}>
      {result.message}
    </div>
  );
}

/**
 * Service configuration section wrapper
 */
function ServiceSection({ title, service, settings, updateSetting, testing, testResult, onTest, children }) {
  const serviceSettings = settings[service] || {};
  const hasRequiredFields = service === 'plex'
    ? serviceSettings.url && serviceSettings.token
    : serviceSettings.url && serviceSettings.api_key;

  return (
    <div className="p-4 bg-cyber-darker rounded-lg">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium text-cyber-accent">{title}</h3>
        <TestButton
          service={service}
          disabled={!hasRequiredFields}
          testing={testing}
          testResult={testResult}
          onTest={onTest}
        />
      </div>
      {children}
      <StatusBadge service={service} testResult={testResult} />
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function Settings() {
  // State management
  const [systemInfo, setSystemInfo] = useState(null);
  const [updateStatus, setUpdateStatus] = useState(null);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);
  const [testResults, setTestResults] = useState({});
  const [testing, setTesting] = useState({});

  // Fetch initial data on mount
  useEffect(() => {
    fetchData();
  }, []);

  /**
   * Fetch system info and settings from API
   * Uses the api service for consistent error handling
   */
  const fetchData = async () => {
    try {
      const [infoData, settingsData] = await Promise.all([
        api.get('/api/system/info').catch(() => null),
        api.get('/api/settings').catch(() => null),
      ]);

      if (infoData) setSystemInfo(infoData);
      if (settingsData) setSettings(settingsData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Check for available updates
   * Docker containers will show a message about Docker-based updates
   */
  const checkForUpdates = async () => {
    setCheckingUpdate(true);
    try {
      const data = await api.get('/api/system/update/check');
      setUpdateStatus(data);
    } catch (error) {
      console.error('Failed to check updates:', error);
    } finally {
      setCheckingUpdate(false);
    }
  };

  /**
   * Apply available update (git-based, may not work in Docker)
   */
  const applyUpdate = async () => {
    if (!confirm('Apply update? The app will need to be restarted after the update completes.')) {
      return;
    }

    setUpdating(true);
    try {
      const data = await api.post('/api/system/update/apply');
      alert(data.message);
    } catch (error) {
      alert(`Update failed: ${error.message}`);
    } finally {
      setUpdating(false);
    }
  };

  /**
   * Save all settings to the backend
   * The API handles filtering out masked values to preserve secrets
   */
  const saveSettings = async () => {
    setSaveStatus('saving');
    try {
      await api.put('/api/settings', settings);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus(null), 5000);
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveStatus('error');
      setTimeout(() => setSaveStatus(null), 5000);
    }
  };

  /**
   * Test connection to a specific service
   * Maps service names to their test endpoints
   */
  const testConnection = async (service) => {
    setTesting(prev => ({ ...prev, [service]: true }));
    setTestResults(prev => ({ ...prev, [service]: null }));

    try {
      // Map service to endpoint and request body
      const testConfig = {
        plex: {
          endpoint: '/api/setup/test/plex',
          body: { url: settings.plex?.url, token: settings.plex?.token }
        },
        radarr: {
          endpoint: '/api/setup/test/radarr',
          body: { url: settings.radarr?.url, api_key: settings.radarr?.api_key }
        },
        sonarr: {
          endpoint: '/api/setup/test/sonarr',
          body: { url: settings.sonarr?.url, api_key: settings.sonarr?.api_key }
        },
        bazarr: {
          endpoint: '/api/setup/test/bazarr',
          body: { url: settings.bazarr?.url, api_key: settings.bazarr?.api_key }
        },
        ollama: {
          endpoint: '/api/setup/test/ai',
          body: { ollama_url: settings.ai?.ollama_url }
        },
      };

      const config = testConfig[service];
      if (!config) return;

      const data = await api.post(config.endpoint, config.body);
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

  /**
   * Update a specific setting value
   * Maintains immutability for React state updates
   */
  const updateSetting = (section, key, value) => {
    setSettings(prev => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: value,
      },
    }));
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-cyber-accent" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Page Header */}
      <div className="flex items-center gap-3">
        <SettingsIcon className="w-8 h-8 text-cyber-accent" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>

      {/* Save Status Banner - Shows feedback after save attempts */}
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

      {/* System Information Card */}
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

      {/* Updates Card */}
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
          <ServiceSection
            title="Plex Media Server"
            service="plex"
            settings={settings}
            updateSetting={updateSetting}
            testing={testing}
            testResult={testResults}
            onTest={testConnection}
          >
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
          </ServiceSection>

          {/* Radarr */}
          <ServiceSection
            title="Radarr (Movies)"
            service="radarr"
            settings={settings}
            updateSetting={updateSetting}
            testing={testing}
            testResult={testResults}
            onTest={testConnection}
          >
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
          </ServiceSection>

          {/* Sonarr */}
          <ServiceSection
            title="Sonarr (TV Shows)"
            service="sonarr"
            settings={settings}
            updateSetting={updateSetting}
            testing={testing}
            testResult={testResults}
            onTest={testConnection}
          >
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
          </ServiceSection>

          {/* Bazarr */}
          <ServiceSection
            title="Bazarr (Subtitles)"
            service="bazarr"
            settings={settings}
            updateSetting={updateSetting}
            testing={testing}
            testResult={testResults}
            onTest={testConnection}
          >
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
          </ServiceSection>
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
              <TestButton
                service="ollama"
                disabled={!settings.ai?.ollama_url}
                testing={testing}
                testResult={testResults}
                onTest={testConnection}
              />
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
            <StatusBadge service="ollama" testResult={testResults} />
          </div>
        </div>
      </div>

      {/* Save Button - Sticky at bottom */}
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
