/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef7ff',
          100: '#d9edff',
          200: '#bce0ff',
          300: '#8eccff',
          400: '#59b0ff',
          500: '#338dff',
          600: '#1a6df5',
          700: '#1457e1',
          800: '#1746b6',
          900: '#193d8f',
          950: '#142757',
        },
        surface: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        tactical: {
          dark: '#030704',     // Pitch black with greenish tint
          panel: '#0a120d',    // Slightly lighter for panels
          border: '#102a1c',   // Dark green borders
          green: '#00ff41',    // Neon Matrix Green
          greenDim: '#008f11', // Dim Matrix Green
          amber: '#ffb000',    // Alert Amber
          red: '#ff003c',      // Laser red
        }
      },
      animation: {
        'scanline': 'scanline 8s linear infinite',
        'flicker': 'flicker 0.15s infinite',
        'radar': 'radar 4s linear infinite',
      },
      keyframes: {
        scanline: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        flicker: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.8 },
        },
        radar: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        }
      },
    },
  },
  plugins: [],
}
