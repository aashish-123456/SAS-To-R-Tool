/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        blue: {
          50: '#eef3f8',
          100: '#d6e1ec',
          200: '#b2c7da',
          300: '#87a7c3',
          400: '#5c86ad',
          500: '#3f6f97',
          600: '#1f4368',
          700: '#193a5a',
          800: '#15324c',
          900: '#112a40',
        },
        primary: {
          50: '#eef3f8',
          100: '#d6e1ec',
          200: '#b2c7da',
          300: '#87a7c3',
          400: '#5c86ad',
          500: '#3f6f97',
          600: '#1f4368',
          700: '#193a5a',
          800: '#15324c',
          900: '#112a40',
        },
      },
    },
  },
  plugins: [],
}
