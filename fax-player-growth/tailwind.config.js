/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        development: "#dcfce7",
        peak: "#5eead4",
        decline1: "#fecaca",
        decline2: "#fca5a5",
        decline3: "#f87171",
      },
    },
  },
  plugins: [],
};
