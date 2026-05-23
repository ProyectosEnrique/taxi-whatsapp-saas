/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'taxi-yellow': '#FFC107',
        'taxi-green': '#4CAF50',
        'taxi-blue': '#2196F3',
      }
    },
  },
  plugins: [],
}
