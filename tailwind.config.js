/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#f9f9f9',
        foreground: '#1a1a1a',
        card: '#f9f9f9',
        'card-foreground': '#1a1a1a',
        border: '#e0e0e0',
        primary: {
          DEFAULT: '#2a6f9c',
          foreground: '#ffffff',
        },
        secondary: {
          DEFAULT: '#f0f0f0',
          foreground: '#333333',
        },
        accent: {
          DEFAULT: '#ff8c00',
          foreground: '#ffffff',
        },
        muted: {
          DEFAULT: '#f0f0f0',
          foreground: '#666666',
        },
        destructive: {
          DEFAULT: '#dc3545',
          foreground: '#ffffff',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['Fira Code', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
