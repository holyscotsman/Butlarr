/**
 * Butlarr Logo - Cyberpunk Butler Robot
 * A neon-styled robot butler icon
 */
export default function ButlarrLogo({ size = 40, className = '', animated = false }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${className} ${animated ? 'animate-pulse' : ''}`}
    >
      {/* Glow filter */}
      <defs>
        <filter id="neonGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <linearGradient id="cyanGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00ffff" />
          <stop offset="100%" stopColor="#05d9e8" />
        </linearGradient>
        <linearGradient id="pinkGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ff00ff" />
          <stop offset="100%" stopColor="#ff2a6d" />
        </linearGradient>
      </defs>

      {/* Robot Head - Main body */}
      <rect
        x="12"
        y="14"
        width="40"
        height="36"
        rx="8"
        fill="#0a0a12"
        stroke="url(#cyanGradient)"
        strokeWidth="2"
        filter="url(#neonGlow)"
      />

      {/* Antenna */}
      <line
        x1="32"
        y1="6"
        x2="32"
        y2="14"
        stroke="url(#cyanGradient)"
        strokeWidth="2"
        strokeLinecap="round"
        filter="url(#neonGlow)"
      />
      <circle
        cx="32"
        cy="6"
        r="3"
        fill="#00ffff"
        filter="url(#neonGlow)"
      />

      {/* Eyes - Glowing circles */}
      <circle
        cx="22"
        cy="28"
        r="6"
        fill="#0a0a12"
        stroke="url(#cyanGradient)"
        strokeWidth="2"
      />
      <circle
        cx="22"
        cy="28"
        r="3"
        fill="#00ffff"
        filter="url(#neonGlow)"
      />

      <circle
        cx="42"
        cy="28"
        r="6"
        fill="#0a0a12"
        stroke="url(#cyanGradient)"
        strokeWidth="2"
      />
      <circle
        cx="42"
        cy="28"
        r="3"
        fill="#00ffff"
        filter="url(#neonGlow)"
      />

      {/* Mouth - LED strip style */}
      <rect
        x="20"
        y="40"
        width="24"
        height="4"
        rx="2"
        fill="url(#pinkGradient)"
        filter="url(#neonGlow)"
      />

      {/* Bow tie */}
      <path
        d="M24 52 L20 56 L20 60 L24 56 L32 56 L40 56 L44 60 L44 56 L40 52 L32 52 L24 52Z"
        fill="url(#pinkGradient)"
        filter="url(#neonGlow)"
      />

      {/* Ear panels */}
      <rect
        x="6"
        y="22"
        width="4"
        height="12"
        rx="2"
        fill="url(#cyanGradient)"
        filter="url(#neonGlow)"
      />
      <rect
        x="54"
        y="22"
        width="4"
        height="12"
        rx="2"
        fill="url(#cyanGradient)"
        filter="url(#neonGlow)"
      />

      {/* Decorative lines on head */}
      <line
        x1="18"
        y1="18"
        x2="18"
        y2="20"
        stroke="#00ffff"
        strokeWidth="1"
        opacity="0.6"
      />
      <line
        x1="22"
        y1="18"
        x2="22"
        y2="20"
        stroke="#00ffff"
        strokeWidth="1"
        opacity="0.6"
      />
      <line
        x1="26"
        y1="18"
        x2="26"
        y2="20"
        stroke="#00ffff"
        strokeWidth="1"
        opacity="0.6"
      />
    </svg>
  );
}
