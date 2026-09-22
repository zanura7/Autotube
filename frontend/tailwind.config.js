/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        // Custom colors matching the Pro UI
        background: '#0f172a', // slate-900
        surface: '#1e293b',    // slate-800
        border: '#334155',     // slate-700
        primary: '#4f46e5',    // indigo-600
        primaryHover: '#4338ca', // indigo-700
        textMain: '#f8fafc',   // slate-50
        textMuted: '#94a3b8',  // slate-400
      }
    },
  },
  plugins: [],
}
