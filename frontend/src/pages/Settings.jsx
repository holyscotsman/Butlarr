import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  RefreshCw, 
  Check, 
  AlertCircle,
  Download,
  Server,
  Cpu,
  GitBranch,
  Clock
} from 'lucide-react';

export default function Settings() {
  const [systemInfo, setSystemInfo] = useState(null);
  const [updateStatus, setUpdateStatus] = useState(null);
  const [settings, setSettings] = useState({});
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [saveStatus, setSaveStatus] = useState(null);

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
    try {
      const res = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      });
      
      if (res.ok) {
        setSaveStatus('success');
        setTimeout(() => setSaveStatus(null), 3000);
      } else {
        setSaveStatus('error');
      }
    } catch (error) {
      setSaveStatus('error');
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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3">
        <SettingsIcon className="w-8 h-8 text-blue-500" />
        <h1 className="text-2xl font-bold">Settings</h1>
      </div>

      {/* System Info Card */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Server className="w-5 h-5" />
          System Information
        </h2>
        
        {systemInfo && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-700 rounded p-3">
              <div className="text-sm text-gray-400">Version</div>
              <div className="text-lg font-mono">{systemInfo.version}</div>
            </div>
            <div className="bg-gray-700 rounded p-3">
              <div className="text-sm text-gray-400">Git Commit</div>
              <div className="text-lg font-mono">{systemInfo.git_commit || 'N/A'}</div>
            </div>
            <div className="bg-gray-700 rounded p-3">
              <div className="text-sm text-gray-400">Branch</div>
              <div className="text-lg font-mono">{systemInfo.git_branch || 'N/A'}</div>
            </div>
            <div className="bg-gray-700 rounded p-3">
              <div className="text-sm text-gray-400">Uptime</div>
              <div className="text-lg font-mono">
                {Math.floor(systemInfo.uptime_seconds / 3600)}h {Math.floor((systemInfo.uptime_seconds % 3600) / 60)}m
              </div>
            </div>
          </div>
        )}

        {/* AI Providers */}
        {systemInfo && (
          <div className="mt-4">
            <div className="text-sm text-gray-400 mb-2">AI Providers</div>
            <div className="flex flex-wrap gap-2">
              {systemInfo.ai_providers.map(provider => (
                <span 
                  key={provider}
                  className={`px-3 py-1 rounded-full text-sm ${
                    provider === 'embedded' 
                      ? 'bg-green-600 text-white' 
                      : 'bg-blue-600 text-white'
                  }`}
                >
                  {provider === 'embedded' ? '🤖 Embedded AI' : provider}
                </span>
              ))}
              {systemInfo.ai_providers.length === 0 && (
                <span className="text-yellow-500">No AI providers configured</span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Update Card */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <GitBranch className="w-5 h-5" />
          Updates
        </h2>
        
        <div className="flex items-center gap-4">
          <button
            onClick={checkForUpdates}
            disabled={checkingUpdate}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${checkingUpdate ? 'animate-spin' : ''}`} />
            Check for Updates
          </button>
          
          {updateStatus?.available && (
            <button
              onClick={applyUpdate}
              disabled={updating}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded flex items-center gap-2 disabled:opacity-50"
            >
              <Download className={`w-4 h-4 ${updating ? 'animate-bounce' : ''}`} />
              {updating ? 'Updating...' : 'Apply Update'}
            </button>
          )}
        </div>

        {updateStatus && (
          <div className={`mt-4 p-4 rounded ${
            updateStatus.available ? 'bg-green-900' : 'bg-gray-700'
          }`}>
            {updateStatus.available ? (
              <div className="flex items-center gap-2 text-green-400">
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

        <p className="mt-4 text-sm text-gray-400">
          Auto-update is {systemInfo?.auto_update_enabled ? 'enabled' : 'disabled'}. 
          Updates are checked on container restart.
        </p>
      </div>

      {/* Service Configuration */}
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-lg font-semibold mb-4">Service Connections</h2>
        
        <div className="space-y-4">
          {/* Plex */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Plex URL</label>
              <input
                type="text"
                value={settings.plex?.url || ''}
                onChange={(e) => updateSetting('plex', 'url', e.target.value)}
                placeholder="http://localhost:32400"
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Plex Token</label>
              <input
                type="password"
                value={settings.plex?.token || ''}
                onChange={(e) => updateSetting('plex', 'token', e.target.value)}
                placeholder="Your Plex token"
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Radarr */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Radarr URL</label>
              <input
                type="text"
                value={settings.radarr?.url || ''}
                onChange={(e) => updateSetting('radarr', 'url', e.target.value)}
                placeholder="http://localhost:7878"
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Radarr API Key</label>
              <input
                type="password"
                value={settings.radarr?.api_key || ''}
                onChange={(e) => updateSetting('radarr', 'api_key', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Sonarr */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Sonarr URL</label>
              <input
                type="text"
                value={settings.sonarr?.url || ''}
                onChange={(e) => updateSetting('sonarr', 'url', e.target.value)}
                placeholder="http://localhost:8989"
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Sonarr API Key</label>
              <input
                type="password"
                value={settings.sonarr?.api_key || ''}
                onChange={(e) => updateSetting('sonarr', 'api_key', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          {/* AI Settings */}
          <div className="border-t border-gray-700 pt-4 mt-4">
            <h3 className="text-md font-medium mb-3">AI Configuration</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Anthropic API Key</label>
                <input
                  type="password"
                  value={settings.ai?.anthropic_api_key || ''}
                  onChange={(e) => updateSetting('ai', 'anthropic_api_key', e.target.value)}
                  placeholder="sk-ant-..."
                  className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">OpenAI API Key</label>
                <input
                  type="password"
                  value={settings.ai?.openai_api_key || ''}
                  onChange={(e) => updateSetting('ai', 'openai_api_key', e.target.value)}
                  placeholder="sk-..."
                  className="w-full px-3 py-2 bg-gray-700 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>
            <p className="mt-2 text-sm text-gray-500">
              Leave blank to use embedded AI (slower but free). Cloud APIs are faster and more accurate.
            </p>
          </div>
        </div>

        {/* Save Button */}
        <div className="mt-6 flex items-center gap-4">
          <button
            onClick={saveSettings}
            className="px-6 py-2 bg-green-600 hover:bg-green-700 rounded flex items-center gap-2"
          >
            <Check className="w-4 h-4" />
            Save Settings
          </button>
          
          {saveStatus === 'success' && (
            <span className="text-green-400 flex items-center gap-1">
              <Check className="w-4 h-4" /> Saved!
            </span>
          )}
          {saveStatus === 'error' && (
            <span className="text-red-400 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" /> Failed to save
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
