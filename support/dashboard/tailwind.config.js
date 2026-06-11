/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#C8153C',
        crimson: '#C8153C',
        ink: '#141414',
      },
      fontFamily: {
        display: ['"Public Sans"', '"Noto Sans KR"', 'sans-serif'],
        headline: ['"Public Sans"', '"Noto Sans KR"', 'sans-serif'],
        body: ['"Geist"', '"Noto Sans KR"', 'sans-serif'],
        label: ['"Public Sans"', '"Noto Sans KR"', 'sans-serif'],
        sans: ['"Geist"', '"Noto Sans KR"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        none: '0', sm: '0', DEFAULT: '0', md: '0', lg: '0', xl: '0', '2xl': '0', '3xl': '0', full: '0',
      },
    },
  },
  plugins: [],
}
