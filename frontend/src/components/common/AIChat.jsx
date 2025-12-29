import { useState, useRef, useEffect } from 'react'
import { X, Send, Bot, User, Loader2 } from 'lucide-react'
import { api } from '../../services/api'

export default function AIChat({ isOpen, onClose }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I\'m Butlarr, your AI library assistant. How can I help you today?' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)

    try {
      // api.post returns data directly, not wrapped in .data
      const data = await api.post('/api/ai/chat', {
        message: userMessage,
        conversation_history: messages.map(m => ({ role: m.role, content: m.content }))
      })

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        tokens: data.tokens_used,
        cost: data.cost_usd
      }])
    } catch (error) {
      // Provide helpful error message based on the error type
      let errorMessage = 'Sorry, I encountered an error. Please try again.'
      if (error.message?.includes('No AI provider')) {
        errorMessage = 'No AI provider is available. Please download the embedded AI model in Settings, or configure a cloud API key (Anthropic/OpenAI).'
      } else if (error.message?.includes('disabled')) {
        errorMessage = 'AI assistant is disabled. Enable it in Settings to use this feature.'
      }

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: errorMessage,
        error: true
      }])
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed right-0 top-0 h-full w-96 bg-cyber-panel border-l border-cyber-border z-50 flex flex-col">
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-cyber-border">
        <div className="flex items-center gap-2">
          <Bot className="text-cyber-accent" size={24} />
          <span className="font-semibold">AI Assistant</span>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-cyber-border rounded-lg">
          <X size={20} />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
              msg.role === 'user' ? 'bg-cyber-pink/20' : 'bg-cyber-accent/20'
            }`}>
              {msg.role === 'user' ? <User size={16} className="text-cyber-pink" /> : <Bot size={16} className="text-cyber-accent" />}
            </div>
            <div className={`max-w-[80%] p-3 rounded-lg ${
              msg.role === 'user' 
                ? 'bg-cyber-pink/10 border border-cyber-pink/30' 
                : msg.error 
                  ? 'bg-cyber-red/10 border border-cyber-red/30'
                  : 'bg-cyber-darker border border-cyber-border'
            }`}>
              <p className="text-sm">{msg.content}</p>
              {msg.tokens && (
                <p className="text-xs text-gray-500 mt-2">
                  {msg.tokens} tokens · ${msg.cost?.toFixed(4)}
                </p>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-lg bg-cyber-accent/20 flex items-center justify-center">
              <Bot size={16} className="text-cyber-accent" />
            </div>
            <div className="bg-cyber-darker border border-cyber-border p-3 rounded-lg">
              <Loader2 className="animate-spin text-cyber-accent" size={16} />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="p-4 border-t border-cyber-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything..."
            className="cyber-input flex-1"
            disabled={loading}
          />
          <button 
            type="submit" 
            disabled={loading || !input.trim()}
            className="cyber-button-primary px-4"
          >
            <Send size={18} />
          </button>
        </div>
      </form>
    </div>
  )
}
