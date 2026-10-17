/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#E8F8F0',
          100: '#D1F1E1',
          500: '#05C168',
          600: '#04A85A',
          700: '#038E4C',
        },
        navy: {
          950: '#0B0F19',
          900: '#0E1524',
          850: '#111827',
          800: '#151D2E',
          700: '#1E293B',
          600: '#2A364F',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'soft': '0 10px 30px -5px rgba(0, 0, 0, 0.04), 0 4px 12px -2px rgba(0, 0, 0, 0.02)',
        'card': '0 14px 34px -8px rgba(15, 23, 42, 0.06), 0 4px 12px -2px rgba(15, 23, 42, 0.02)',
        'card-hover': '0 20px 40px -10px rgba(15, 23, 42, 0.1), 0 6px 16px -3px rgba(15, 23, 42, 0.04)',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
}
