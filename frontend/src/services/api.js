/**
 * Butlarr API Service
 * Handles all HTTP and WebSocket communication with the backend
 */

// API base URL - works in both development and production
const getApiBase = () => {
  // In production (Docker), we're served from the same origin
  if (import.meta.env.PROD) {
    return ''
  }
  // In development, use the Vite proxy
  return ''
}

const API_BASE = getApiBase()

class ApiService {
  constructor() {
    this.baseUrl = API_BASE
  }

  async request(method, endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`
    
    const config = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }
    
    if (options.body && typeof options.body === 'object') {
      config.body = JSON.stringify(options.body)
    }
    
    try {
      const response = await fetch(url, config)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`)
      }
      
      // Handle empty responses
      const text = await response.text()
      return text ? JSON.parse(text) : {}
    } catch (error) {
      console.error(`API Error [${method} ${endpoint}]:`, error)
      throw error
    }
  }

  get(endpoint, options = {}) {
    return this.request('GET', endpoint, options)
  }

  post(endpoint, data, options = {}) {
    return this.request('POST', endpoint, { ...options, body: data })
  }

  put(endpoint, data, options = {}) {
    return this.request('PUT', endpoint, { ...options, body: data })
  }

  delete(endpoint, options = {}) {
    return this.request('DELETE', endpoint, options)
  }
}


class WebSocketService {
  constructor() {
    this.connections = new Map()
    this.reconnectAttempts = new Map()
    this.maxReconnectAttempts = 10
    this.reconnectDelay = 1000
    this.heartbeatInterval = 30000
  }

  getWsUrl(channel) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/ws/${channel}`
  }

  connect(channel, onMessage, onError) {
    if (this.connections.has(channel)) {
      return this.connections.get(channel)
    }

    const wsUrl = this.getWsUrl(channel)
    console.log(`WebSocket connecting to: ${wsUrl}`)
    
    try {
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        console.log(`WebSocket connected: ${channel}`)
        this.reconnectAttempts.set(channel, 0)
        this.startHeartbeat(channel, ws)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type !== 'pong') {
            onMessage(data)
          }
        } catch (e) {
          console.error('WebSocket parse error:', e)
        }
      }

      ws.onerror = (error) => {
        console.error(`WebSocket error (${channel}):`, error)
        if (onError) onError(error)
      }

      ws.onclose = (event) => {
        console.log(`WebSocket closed (${channel}):`, event.code, event.reason)
        this.stopHeartbeat(channel)
        this.connections.delete(channel)
        
        // Attempt reconnection
        const attempts = this.reconnectAttempts.get(channel) || 0
        if (attempts < this.maxReconnectAttempts && !event.wasClean) {
          this.reconnectAttempts.set(channel, attempts + 1)
          const delay = this.reconnectDelay * Math.pow(2, attempts)
          console.log(`WebSocket reconnecting in ${delay}ms (attempt ${attempts + 1})`)
          setTimeout(() => {
            this.connect(channel, onMessage, onError)
          }, delay)
        }
      }

      this.connections.set(channel, ws)
      return ws
    } catch (error) {
      console.error(`WebSocket connection failed (${channel}):`, error)
      if (onError) onError(error)
      return null
    }
  }

  startHeartbeat(channel, ws) {
    const intervalId = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, this.heartbeatInterval)
    
    ws._heartbeatInterval = intervalId
  }

  stopHeartbeat(channel) {
    const ws = this.connections.get(channel)
    if (ws && ws._heartbeatInterval) {
      clearInterval(ws._heartbeatInterval)
    }
  }

  disconnect(channel) {
    const ws = this.connections.get(channel)
    if (ws) {
      this.stopHeartbeat(channel)
      ws.close(1000, 'Client disconnect')
      this.connections.delete(channel)
      this.reconnectAttempts.delete(channel)
    }
  }

  disconnectAll() {
    for (const channel of this.connections.keys()) {
      this.disconnect(channel)
    }
  }

  send(channel, data) {
    const ws = this.connections.get(channel)
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
      return true
    }
    return false
  }

  isConnected(channel) {
    const ws = this.connections.get(channel)
    return ws && ws.readyState === WebSocket.OPEN
  }
}


// Export singleton instances
export const api = new ApiService()
export const ws = new WebSocketService()

// Re-export for compatibility
export default { api, ws }
