import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Sparkles,
  Trash2,
  AlertTriangle,
  HardDrive,
  Activity,
  Settings,
  MessageSquare,
  Menu,
  X,
  Zap,
  FileText
} from 'lucide-react'
import { useState, useEffect } from 'react'
import AIChat from './AIChat'
import ButlarrLogo from './ButlarrLogo'

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/recommendations', icon: Sparkles, label: 'Recommendations' },
  { path: '/bad-movies', icon: Trash2, label: 'Bad Movies' },
  { path: '/issues', icon: AlertTriangle, label: 'Issues' },
  { path: '/storage', icon: HardDrive, label: 'Storage' },
  { path: '/activity', icon: Activity, label: 'Activity' },
  { path: '/settings', icon: Settings, label: 'Settings' },
  { path: '/logs', icon: FileText, label: 'Logs' },
]

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [chatOpen, setChatOpen] = useState(false)
  const [version, setVersion] = useState(null) // Fetched from API - single source of truth
  const [glitchEnabled, setGlitchEnabled] = useState(() => {
    // Load from localStorage
    const saved = localStorage.getItem('butlarr-glitch')
    return saved === 'true'
  })

  // Fetch version from API on mount - ensures frontend always shows correct version
  useEffect(() => {
    fetch('/api/system/info')
      .then(res => res.ok ? res.json() : null)
      .then(data => data && setVersion(data.version))
      .catch(() => {}) // Silently fail - version display is non-critical
  }, [])

  // Apply glitch class to body
  useEffect(() => {
    if (glitchEnabled) {
      document.body.classList.add('glitch-enabled')
    } else {
      document.body.classList.remove('glitch-enabled')
    }
    localStorage.setItem('butlarr-glitch', glitchEnabled)
  }, [glitchEnabled])

  return (
    <div className="min-h-screen bg-cyber-dark cyber-grid">
      {/* Scanline effect */}
      <div className="scanline" />
      
      {/* Sidebar */}
      <aside className={`fixed left-0 top-0 h-full bg-cyber-panel border-r border-cyber-border z-40 transition-all duration-300 ${sidebarOpen ? 'w-64' : 'w-16'}`}>
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-cyber-border">
          {sidebarOpen ? (
            <div className="flex items-center gap-2">
              <ButlarrLogo size={36} animated={glitchEnabled} />
              <span className={`font-bold text-xl text-cyber-accent ${glitchEnabled ? 'glitch-text logo-glitch' : ''}`} data-text="Butlarr">Butlarr</span>
            </div>
          ) : (
            <ButlarrLogo size={32} animated={glitchEnabled} />
          )}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-2 hover:bg-cyber-border rounded-lg transition-colors"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-3 space-y-1">
          {navItems.map(({ path, icon: Icon, label }) => (
            <NavLink
              key={path}
              to={path}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all
                ${isActive 
                  ? 'bg-cyber-accent/10 text-cyber-accent border border-cyber-accent/30' 
                  : 'text-gray-400 hover:text-white hover:bg-cyber-border/50'
                }
              `}
            >
              <Icon size={20} />
              {sidebarOpen && <span className="font-medium">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Version - fetched from API for consistency */}
        {sidebarOpen && version && (
          <div className="absolute bottom-4 left-4 right-4 text-center">
            <span className="text-sm text-cyber-accent/70 font-mono cyber-glow">v{version}</span>
          </div>
        )}
      </aside>

      {/* Main content */}
      <main className={`transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-16'}`}>
        {/* Header */}
        <header className="h-20 bg-cyber-panel/80 backdrop-blur border-b border-cyber-border flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold">AI-Powered Plex Library Management</h1>
          </div>
          <div className="flex items-center gap-3">
            {version && <span className="text-sm text-gray-500 font-mono">v{version}</span>}
            {/* Glitch toggle */}
            <button
              onClick={() => setGlitchEnabled(!glitchEnabled)}
              title={glitchEnabled ? 'Disable glitch effects' : 'Enable glitch effects'}
              className={`p-2 rounded-lg transition-all ${glitchEnabled ? 'bg-cyber-pink/20 text-cyber-pink border border-cyber-pink/50' : 'text-gray-500 hover:bg-cyber-border hover:text-gray-300'}`}
            >
              <Zap size={20} className={glitchEnabled ? 'animate-pulse' : ''} />
            </button>
            <button
              onClick={() => setChatOpen(!chatOpen)}
              className={`p-3 rounded-lg transition-all ${chatOpen ? 'bg-cyber-accent text-cyber-dark' : 'hover:bg-cyber-border'}`}
            >
              <MessageSquare size={24} />
            </button>
          </div>
        </header>

        {/* Page content */}
        <div className="p-6">
          {children}
        </div>
      </main>

      {/* AI Chat Drawer */}
      <AIChat isOpen={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
