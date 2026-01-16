/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'rgb(var(--bg-primary) / <alpha-value>)',
        surface: 'rgb(var(--bg-secondary) / <alpha-value>)',
        card: 'rgb(var(--bg-card) / <alpha-value>)',

        primary: {
          DEFAULT: 'rgb(var(--accent-primary) / <alpha-value>)',
          glow: 'rgb(var(--accent-glow) / <alpha-value>)',
        },

        muted: 'rgb(var(--text-muted) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'spin': 'spin 1s linear infinite',
        'ping': 'ping 1s cubic-bezier(0, 0, 0.2, 1) infinite',
        'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce': 'bounce 1s infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgb(var(--accent-primary) / 0.2)' },
          '100%': { boxShadow: '0 0 20px rgb(var(--accent-primary) / 0.6)' },
        }
      }
    },
  },
  plugins: [],
}
