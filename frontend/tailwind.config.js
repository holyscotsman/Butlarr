/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Cyberpunk color palette
        cyber: {
          dark: '#0a0a0f',
          darker: '#050508',
          panel: '#12121a',
          border: '#1e1e2e',
          accent: '#00ffff',
          'accent-dim': '#00cccc',
          pink: '#ff00ff',
          'pink-dim': '#cc00cc',
          purple: '#9945ff',
          green: '#00ff9f',
          yellow: '#ffff00',
          orange: '#ff9500',
          red: '#ff3366',
          blue: '#0099ff',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        'cyber': '0 0 10px rgba(0, 255, 255, 0.3)',
        'cyber-lg': '0 0 20px rgba(0, 255, 255, 0.4)',
        'cyber-pink': '0 0 10px rgba(255, 0, 255, 0.3)',
        'glow': '0 0 30px rgba(0, 255, 255, 0.2)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'scan': 'scan 2s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100%)' },
        },
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(0, 255, 255, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 255, 255, 0.4)' },
        },
      },
    },
  },
  plugins: [],
}
